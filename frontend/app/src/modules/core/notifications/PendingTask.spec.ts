import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { msg } from '@/message-key';
import PendingTask from '@/modules/core/notifications/PendingTask.vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
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

function createWrapper(props: Partial<InstanceType<typeof PendingTask>['$props']> = {}): VueWrapper {
  return mount(PendingTask, {
    props: {
      activity: activity(),
      cancellable: false,
      now: NOW,
      percentage: -1,
      ...props,
    },
  });
}

describe('pendingTask', () => {
  const ADDRESS = '0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1';

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show the title and subtitle at the top level', () => {
    const text = createWrapper({ activity: activity({ subtitle: 'Ethereum' }) }).text();

    expect(text).toContain('Transaction sync');
    expect(text).toContain('Ethereum');
  });

  it('should show only its own identity when nested', () => {
    const text = createWrapper({
      activity: activity({ subtitle: 'Ethereum' }),
      nested: true,
    }).text();

    expect(text).toContain('Ethereum');
    expect(text).not.toContain('Transaction sync');
  });

  it('should render elapsed time for running work', () => {
    const text = createWrapper({ activity: activity({ startedAt: NOW - 14_000 }) }).text();

    expect(text).toContain('14s');
  });

  it('should not render elapsed time once the work settled', () => {
    const text = createWrapper({
      activity: activity({ startedAt: NOW - 14_000, status: ActivityStatus.COMPLETE }),
    }).text();

    expect(text).not.toContain('14s');
  });

  it('should render its subtree tally next to the elapsed time', () => {
    const text = createWrapper({
      activity: activity({ startedAt: NOW - 5000 }),
      percentage: 25,
      steps: { current: 1, total: 4 },
    }).text();

    expect(text).toContain('pending_task.steps::1, 4');
  });

  function outcomeLabel(wrapper: VueWrapper): string | undefined {
    return wrapper.find('[data-testid=activity-outcome]').attributes('aria-label');
  }

  it.each([
    [ActivityStatus.PENDING, 'pending_task.status.queued'],
    [ActivityStatus.FAILED, 'pending_task.status.failed'],
    [ActivityStatus.SKIPPED, 'pending_task.status.skipped'],
    [ActivityStatus.CANCELLED, 'pending_task.status.cancelled'],
    [ActivityStatus.COMPLETE, 'pending_task.status.done'],
  ])('should label a %s row with its outcome', (status, key) => {
    expect(outcomeLabel(createWrapper({ activity: activity({ status }) }))).toBe(key);
  });

  it.each([
    [ActivityStatus.FAILED, 'network unreachable after retries'],
    [ActivityStatus.SKIPPED, 'disabled in settings'],
  ])('should caption a %s row with the producer reason', (status, reason) => {
    const label = outcomeLabel(createWrapper({ activity: activity({ reason, status }) }));

    expect(label).toContain(reason);
    expect(label).toContain('pending_task.status.with_reason');
  });

  it('should leave a row without a reason on the bare status, with no empty suffix', () => {
    const label = outcomeLabel(createWrapper({ activity: activity({ status: ActivityStatus.FAILED }) }));

    expect(label).toBe('pending_task.status.failed');
  });

  it('should label a running row with no percentage instead of spinning', () => {
    const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.RUNNING }), percentage: -1 });

    expect(outcomeLabel(wrapper)).toBe('pending_task.status.running');
    expect(wrapper.findComponent({ name: 'RuiProgress' }).exists()).toBe(false);
  });

  it('should show the outcome as an icon, not a word', () => {
    const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.COMPLETE }) });

    expect(wrapper.text()).not.toContain('pending_task.status.done');
    expect(wrapper.find('[data-testid=activity-outcome]').exists()).toBe(true);
  });

  it('should present the outcome as an image, not a focusable button, since RuiChip defaults to both', () => {
    const chip = createWrapper({ activity: activity({ status: ActivityStatus.COMPLETE }) })
      .find('[data-testid=activity-outcome]');

    expect(chip.attributes('role')).toBe('img');
    expect(chip.attributes('tabindex')).toBe('-1');
  });

  it('should show a determinate ring once there is a percentage', () => {
    const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.RUNNING }), percentage: 40 });

    const progress = wrapper.findComponent({ name: 'RuiProgress' });
    expect(progress.props('variant')).toBe('determinate');
    expect(progress.props('value')).toBe(40);
    expect(wrapper.find('[data-testid=activity-outcome]').exists()).toBe(false);
  });

  it('should prefer the outcome chip to the ring once the work has settled, percentage or not', () => {
    const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.FAILED }), percentage: 40 });

    expect(outcomeLabel(wrapper)).toBe('pending_task.status.failed');
    expect(wrapper.findComponent({ name: 'RuiProgress' }).exists()).toBe(false);
  });

  it('should emit cancel only when the caller allows it', async () => {
    const wrapper = createWrapper({ cancellable: true });
    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('cancel')).toHaveLength(1);
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

  it('should render no cancel control when the caller withholds it', () => {
    expect(createWrapper({ cancellable: false }).find('button').exists()).toBe(false);
  });
});
