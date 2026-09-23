import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { msg } from '@/message-key';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import DockActivityRow from '@/modules/task-center/components/DockActivityRow.vue';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
  WaitingReason,
} from '@/modules/task-center/core/types';

const NOW = 1_000_000;

function activity(partial: Partial<Activity> = {}): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.TX_SYNC, 'ethereum'),
    kind: ActivityKind.TX_SYNC,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    title: 'Transaction sync',
    ...partial,
  };
}

function createWrapper(props: Partial<InstanceType<typeof DockActivityRow>['$props']> = {}): VueWrapper {
  return mount(DockActivityRow, {
    props: {
      activity: activity(),
      now: NOW,
      percentage: -1,
      ...props,
    },
  });
}

function outcomeLabel(wrapper: VueWrapper): string | undefined {
  return wrapper.find('[data-testid=activity-outcome]').attributes('aria-label');
}

describe('dockActivityRow', () => {
  const ADDRESS = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should expose the status it shows, the outcome a parent passes down included', () => {
    const row = (wrapper: VueWrapper): string | undefined =>
      wrapper.find('[data-testid=dock-activity-row]').attributes('data-status');

    expect(row(createWrapper())).toBe(ActivityStatus.RUNNING);
    expect(row(createWrapper({ activity: activity({ status: ActivityStatus.CANCELLED }) }))).toBe(ActivityStatus.CANCELLED);
    expect(row(createWrapper({ activity: activity({ status: ActivityStatus.COMPLETE }), outcomeStatus: ActivityStatus.FAILED }))).toBe(ActivityStatus.FAILED);
  });

  describe('why it waits', () => {
    it('should say why a queued row has not started', () => {
      const wrapper = createWrapper({
        activity: activity({ status: ActivityStatus.PENDING, waiting: { reason: WaitingReason.HISTORY_SYNC } }),
      });

      expect(wrapper.find('[data-testid=activity-waiting]').text()).toBe('task_dock.waiting.history_sync');
    });

    it('should leave the line out for a row that is not waiting', () => {
      expect(createWrapper().find('[data-testid=activity-waiting]').exists()).toBe(false);
    });
  });

  describe('what it names', () => {
    it('should show the title and subtitle at the top level', () => {
      const text = createWrapper({ activity: activity({ subtitle: 'Ethereum' }) }).text();

      expect(text).toContain('Transaction sync');
      expect(text).toContain('Ethereum');
    });

    it('should show only its own identity when nested', () => {
      const text = createWrapper({ activity: activity({ subtitle: 'Ethereum' }), parent: activity({ title: 'History refresh' }) }).text();

      expect(text).toContain('Ethereum');
      expect(text).not.toContain('Transaction sync');
    });

    it('should scramble an address in the subtitle while privacy mode is on', () => {
      useSettingsRepo().updateFrontend({ scrambleData: true, scrambleMultiplier: 7 });

      const text = createWrapper({
        activity: activity({
          subtitle: { key: msg.$t('task_center.activity.tx_sync.address'), params: { address: ADDRESS, chain: 'Ethereum' } },
        }),
      }).text();

      expect(text).not.toContain(ADDRESS);
    });

    it('should leave the address alone while privacy mode is off', () => {
      useSettingsRepo().updateFrontend({ scrambleData: false });

      const text = createWrapper({
        activity: activity({
          subtitle: { key: msg.$t('task_center.activity.tx_sync.address'), params: { address: ADDRESS, chain: 'Ethereum' } },
        }),
      }).text();

      expect(text).toContain(ADDRESS);
    });

    it('should show the chain icon of what the row acts on', () => {
      const icon = createWrapper().findComponent({ name: 'ChainIcon' });

      expect(icon.exists()).toBe(true);
      expect(icon.props('chain')).toBe('ethereum');
    });

    it('should show the location icon of an exchange row', () => {
      const wrapper = createWrapper({
        activity: activity({ id: makeActivityId(ActivityKind.EXCHANGE_EVENTS, 'kraken', 'main'), kind: ActivityKind.EXCHANGE_EVENTS }),
      });

      expect(wrapper.findComponent({ name: 'LocationIcon' }).props('item')).toBe('kraken');
      expect(wrapper.findComponent({ name: 'ChainIcon' }).exists()).toBe(false);
    });

    it('should leave out the chain icon its parent\'s row already shows, and keep one that differs', () => {
      const account = activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'eth', ADDRESS) });
      const icon = (parent: Activity): boolean => createWrapper({ activity: account, parent }).findComponent({ name: 'ChainIcon' }).exists();

      expect(icon(activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'eth') }))).toBe(false);
      expect(icon(activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'optimism') }))).toBe(true);
    });

    it('should leave out the location icon its parent\'s row already shows', () => {
      const exchange = (name: string): Activity => activity({ id: makeActivityId(ActivityKind.EXCHANGE_EVENTS, 'kraken', name), kind: ActivityKind.EXCHANGE_EVENTS });

      const wrapper = createWrapper({ activity: exchange('second'), parent: exchange('main') });

      expect(wrapper.findComponent({ name: 'LocationIcon' }).exists()).toBe(false);
    });

    it('should keep an empty icon column on a nested row with no icon, so its label lines up with its siblings\'', () => {
      const prices = activity({ id: makeActivityId(ActivityKind.PRICES, 'latest'), kind: ActivityKind.PRICES });

      const nested = createWrapper({ activity: prices, parent: activity() });
      expect(nested.find('[data-testid=dock-subject-icon-column]').exists()).toBe(true);
      expect(nested.find('[data-testid=dock-subject-icon]').exists()).toBe(false);

      expect(createWrapper({ activity: prices }).find('[data-testid=dock-subject-icon-column]').exists()).toBe(false);
    });

    it('should give a nested account row no icon column, since its avatar takes that place', () => {
      const account = activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'eth', ADDRESS) });

      const wrapper = createWrapper({ activity: account, parent: activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'eth') }) });

      expect(wrapper.find('[data-testid=dock-subject-icon-column]').exists()).toBe(false);
    });

    it('should fade a settled nested label but keep a settled job\'s title at full strength', () => {
      const label = (wrapper: VueWrapper): string[] => wrapper.find('[data-testid=activity-label]').classes();
      const settled = activity({ status: ActivityStatus.COMPLETE });
      const parent = activity({ id: makeActivityId(ActivityKind.PRICES, 'latest'), kind: ActivityKind.PRICES });

      expect(label(createWrapper({ activity: settled }))).not.toContain('text-rui-text-secondary');
      expect(label(createWrapper({ activity: settled, parent }))).toContain('text-rui-text-secondary');
      expect(label(createWrapper({ activity: activity(), parent }))).not.toContain('text-rui-text-secondary');
    });

    it('should show no subject icon for work that acts on no chain or location', () => {
      const wrapper = createWrapper({ activity: activity({ id: makeActivityId(ActivityKind.PRICES, 'latest'), kind: ActivityKind.PRICES }) });

      expect(wrapper.find('[data-testid=dock-subject-icon]').exists()).toBe(false);
    });

    it('should link a nested account row\'s address on its chain, and leave a top-level one as text', () => {
      const account = activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'eth', ADDRESS), subtitle: 'Account' });

      const nested = createWrapper({ activity: account, parent: activity() }).findComponent({ name: 'HashLink' });
      expect(nested.props('text')).toBe(ADDRESS);
      expect(nested.props('location')).toBe('eth');

      expect(createWrapper({ activity: account }).findComponent({ name: 'HashLink' }).exists()).toBe(false);
    });

    it('should keep a nested account\'s copy and explorer buttons out of sight until the address is hovered', () => {
      const account = activity({ id: makeActivityId(ActivityKind.TX_SYNC, 'eth', ADDRESS), subtitle: 'Account' });

      const link = createWrapper({ activity: account, parent: activity() }).findComponent({ name: 'HashLink' });

      expect(link.props('revealActions')).toBe(true);
    });

    it('should scramble every address when a batch joins several into one param', () => {
      const second = '0x9531C059098e3d194fF87FebB587aB07B30B1306';
      useSettingsRepo().updateFrontend({ scrambleData: true, scrambleMultiplier: 7 });

      const text = createWrapper({
        activity: activity({
          subtitle: { key: msg.$t('task_center.activity.accounts.add'), params: { address: `${ADDRESS},\n${second}` } },
        }),
      }).text();

      expect(text).not.toContain(ADDRESS);
      expect(text).not.toContain(second);
    });
  });

  describe('its progress', () => {
    it('should render elapsed time for running work', () => {
      expect(createWrapper({ activity: activity({ startedAt: NOW - 14_000 }) }).text()).toContain('14s');
    });

    it('should not render elapsed time once the work settled', () => {
      const text = createWrapper({ activity: activity({ startedAt: NOW - 14_000, status: ActivityStatus.COMPLETE }) }).text();

      expect(text).not.toContain('14s');
    });

    it('should show a bar with the subtree tally beside it once there is a percentage', () => {
      const wrapper = createWrapper({ percentage: 25, steps: { current: 1, total: 4 } });

      const meter = wrapper.find('[data-testid=activity-meter]');
      expect(meter.exists()).toBe(true);
      expect(meter.text()).toBe('pending_task.steps::1, 4');
      expect(wrapper.findComponent({ name: 'RuiProgress' }).props('value')).toBe(25);
    });

    it('should put a leaf\'s own percentage beside the bar when it has no tally', () => {
      expect(createWrapper({ percentage: 40 }).find('[data-testid=activity-meter]').text()).toBe('percentage_display.value::40');
    });

    it('should count a leaf\'s own steps beside its bar, and once it settles', () => {
      const decode = (status: ActivityStatus): Activity => activity({
        id: makeActivityId(ActivityKind.TX_DECODING, 'eth', 'cached'),
        kind: ActivityKind.TX_DECODING,
        status,
        steps: { current: 1234, total: 5000 },
      });

      expect(createWrapper({ activity: decode(ActivityStatus.RUNNING), percentage: 25 }).find('[data-testid=activity-meter]').text())
        .toBe('pending_task.steps::1234, 5000');
      expect(createWrapper({ activity: decode(ActivityStatus.COMPLETE), parent: activity() }).text()).toContain('pending_task.steps::1234, 5000');
    });

    it('should give a nested leaf only its ring, not a second bar under its parent\'s', () => {
      const wrapper = createWrapper({ parent: activity(), percentage: 40 });

      expect(wrapper.findComponent({ name: 'RuiProgress' }).props('value')).toBe(40);
      expect(wrapper.find('[data-testid=activity-meter]').exists()).toBe(false);
    });

    it('should keep the bar on a nested parent, which rolls up the rows under it', () => {
      const wrapper = createWrapper({ parent: activity(), percentage: 25, steps: { current: 1, total: 4 } });

      expect(wrapper.find('[data-testid=activity-meter]').text()).toBe('pending_task.steps::1, 4');
    });

    it('should keep a running nested leaf\'s own tally as text, with no bar', () => {
      const wrapper = createWrapper({
        activity: activity({
          id: makeActivityId(ActivityKind.TX_DECODING, 'eth', 'cached'),
          kind: ActivityKind.TX_DECODING,
          steps: { current: 1234, total: 5000 },
        }),
        parent: activity(),
        percentage: 25,
      });

      expect(wrapper.find('[data-testid=activity-meter]').exists()).toBe(false);
      expect(wrapper.text()).toContain('pending_task.steps::1234, 5000');
    });

    it('should keep an account sync at a percentage, since its steps are seconds of range', () => {
      const account = activity({ steps: { current: 86_400, total: 604_800 } });

      expect(createWrapper({ activity: account, percentage: 14 }).find('[data-testid=activity-meter]').text()).toBe('percentage_display.value::14');
    });

    it('should mark a running row with no percentage by its status, with no ring and no bar', () => {
      const wrapper = createWrapper({ percentage: -1 });

      expect(outcomeLabel(wrapper)).toBe('pending_task.status.running');
      expect(wrapper.findComponent({ name: 'RuiProgress' }).exists()).toBe(false);
      expect(wrapper.find('[data-testid=activity-meter]').exists()).toBe(false);
    });

    it('should take less room for a settled child with nothing but its name, and the usual room otherwise', () => {
      const row = (partial: Partial<Activity>): string[] => createWrapper({ activity: activity(partial), parent: activity() })
        .find('[data-testid=dock-activity-row]')
        .classes();

      expect(row({ status: ActivityStatus.COMPLETE })).toContain('py-0.5');
      expect(row({ reason: 'no accounts', status: ActivityStatus.SKIPPED })).toContain('py-1.5');
      expect(row({ status: ActivityStatus.RUNNING })).toContain('py-1.5');
    });

    it('should keep a settled parent\'s tally as text, with no bar', () => {
      const wrapper = createWrapper({
        activity: activity({ status: ActivityStatus.COMPLETE }),
        percentage: 100,
        steps: { current: 4, total: 4 },
      });

      expect(wrapper.find('[data-testid=activity-meter]').exists()).toBe(false);
      expect(wrapper.text()).toContain('pending_task.steps::4, 4');
    });
  });

  describe('its outcome', () => {
    it.each([
      [ActivityStatus.PENDING, 'pending_task.status.queued'],
      [ActivityStatus.FAILED, 'pending_task.status.failed'],
      [ActivityStatus.SKIPPED, 'pending_task.status.skipped'],
      [ActivityStatus.CANCELLED, 'pending_task.status.cancelled'],
      [ActivityStatus.COMPLETE, 'pending_task.status.done'],
    ])('should label a %s row with its outcome, as an image', (status, key) => {
      const mark = createWrapper({ activity: activity({ status }) }).find('[data-testid=activity-outcome]');

      expect(mark.attributes('aria-label')).toBe(key);
      expect(mark.attributes('role')).toBe('img');
    });

    it('should report the status its caller passes over its own', () => {
      const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.COMPLETE }), outcomeStatus: ActivityStatus.FAILED });

      expect(outcomeLabel(wrapper)).toBe('pending_task.status.failed');
    });

    it.each([
      [ActivityStatus.FAILED, 'network unreachable after retries', 'text-rui-error'],
      [ActivityStatus.SKIPPED, 'disabled in settings', 'text-rui-warning'],
    ])('should show a %s row\'s reason on the row, not only in its mark', (status, reason, color) => {
      const wrapper = createWrapper({ activity: activity({ reason, status }) });

      const line = wrapper.find('[data-testid=activity-reason]');
      expect(line.text()).toBe(reason);
      expect(line.classes()).toContain(color);
      expect(outcomeLabel(wrapper)).toContain('pending_task.status.with_reason');
    });

    it('should show no reason line, and a bare status, for a row without a reason', () => {
      const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.FAILED }) });

      expect(wrapper.find('[data-testid=activity-reason]').exists()).toBe(false);
      expect(outcomeLabel(wrapper)).toBe('pending_task.status.failed');
    });

    it('should prefer the outcome mark to the ring once the work has settled, percentage or not', () => {
      const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.FAILED }), percentage: 40 });

      expect(outcomeLabel(wrapper)).toBe('pending_task.status.failed');
      expect(wrapper.findComponent({ name: 'RuiProgress' }).exists()).toBe(false);
    });
  });

  describe('its controls', () => {
    it('should emit cancel for work that can be cancelled', async () => {
      const wrapper = createWrapper();
      await wrapper.find('[data-testid=cancel-activity]').trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
    });

    it('should name the cancel icon button for assistive technology', () => {
      expect(createWrapper().find('[data-testid=cancel-activity]').attributes('aria-label')).toBe('collapsed_pending_tasks.cancel_task');
    });

    it('should render no cancel control for work that cannot be cancelled', () => {
      expect(createWrapper({ activity: activity({ cancellable: false }) }).find('[data-testid=cancel-activity]').exists()).toBe(false);
    });

    it('should render no cancel control once the work settled', () => {
      const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.FAILED }) });

      expect(wrapper.find('[data-testid=cancel-activity]').exists()).toBe(false);
    });

    it('should offer retry on a failed activity that can run again, and emit it', async () => {
      const failed = activity({ rerunnable: true, status: ActivityStatus.FAILED });
      const wrapper = createWrapper({ activity: failed });

      await wrapper.find('[data-testid=retry-activity]').trigger('click');

      expect(wrapper.emitted('retry')).toEqual([[failed]]);
    });

    it('should offer no retry on a failed activity that cannot run again', () => {
      const wrapper = createWrapper({ activity: activity({ rerunnable: false, status: ActivityStatus.FAILED }) });

      expect(wrapper.find('[data-testid=retry-activity]').exists()).toBe(false);
    });

    it('should offer no retry on a parent that only reports a failure beneath it', () => {
      const wrapper = createWrapper({
        activity: activity({ rerunnable: true, status: ActivityStatus.COMPLETE }),
        outcomeStatus: ActivityStatus.FAILED,
      });

      expect(wrapper.find('[data-testid=retry-activity]').exists()).toBe(false);
    });

    it('should offer dismiss as a labelled icon button', () => {
      const dismiss = createWrapper({ activity: activity({ status: ActivityStatus.COMPLETE }), dismissible: true }).find('[data-testid=dismiss-activity]');

      expect(dismiss.attributes('aria-label')).toBe('pending_task.dismiss');
      expect(dismiss.text()).toBe('lu-x');
    });

    it('should put the toggle last, so every toggle sits in one column at the row\'s end', () => {
      const wrapper = mount(DockActivityRow, {
        props: { activity: activity(), now: NOW, percentage: -1 },
        slots: { toggle: '<button data-testid="toggle-under-test" />' },
      });

      const last = wrapper.findAll('[data-testid=activity-actions] > *').at(-1);
      expect(last?.attributes('data-testid')).toBe('toggle-under-test');
      expect(wrapper.find('[data-testid=activity-toggle-slot]').exists()).toBe(false);
    });

    it('should keep the toggle\'s space on a row with buttons but no toggle, so its buttons line up', () => {
      expect(createWrapper().find('[data-testid=activity-toggle-slot]').exists()).toBe(true);
      expect(createWrapper({ activity: activity({ cancellable: false }) }).find('[data-testid=activity-toggle-slot]').exists()).toBe(false);
    });

    it('should offer no dismiss control unless the caller asks for one', () => {
      expect(createWrapper().find('[data-testid=dismiss-activity]').exists()).toBe(false);
    });

    it('should emit dismiss with its activity when the dismiss control is clicked', async () => {
      const failed = activity({ status: ActivityStatus.FAILED });
      const wrapper = createWrapper({ activity: failed, dismissible: true });

      await wrapper.find('[data-testid=dismiss-activity]').trigger('click');

      expect(wrapper.emitted('dismiss')).toEqual([[failed]]);
    });
  });
});
