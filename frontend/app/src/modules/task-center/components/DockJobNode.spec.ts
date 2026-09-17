import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { assert, beforeEach, describe, expect, it } from 'vitest';
import DockJobNode from '@/modules/task-center/components/DockJobNode.vue';
import { buildTree } from '@/modules/task-center/core/tree';
import {
  type Activity,
  type ActivityId,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';

const NOW = 1_000_000;

function activity(name: string, partial: Partial<Activity> = {}): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.TX_SYNC, name),
    kind: ActivityKind.TX_SYNC,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    subtitle: name,
    title: 'Transaction sync',
    ...partial,
  };
}

function id(name: string): ActivityId {
  return makeActivityId(ActivityKind.TX_SYNC, name);
}

function mountTree(activities: Activity[], props: { depth?: number; dismissible?: boolean } = {}): VueWrapper {
  const { children, roots } = buildTree(activities, (a, b) => a.id.localeCompare(b.id));
  return mount(DockJobNode, { props: { activity: roots[0], children, now: NOW, ...props } });
}

/**
 * A three-level tree, the shape a history refresh actually declares: one job, a chain under it,
 * two accounts under the chain.
 */
function running(): Activity[] {
  return [
    activity('refresh', { kind: ActivityKind.HISTORY_SYNC, subtitle: undefined, title: 'History refresh' }),
    activity('ethereum', { parent: id('refresh') }),
    activity('0xaa', { parent: id('ethereum'), status: ActivityStatus.COMPLETE }),
    activity('0xbb', { parent: id('ethereum') }),
  ];
}

/** The same tree once it settled, with one account failed and able to run again. */
function settled(parent: ActivityStatus): Activity[] {
  return [
    activity('refresh', { kind: ActivityKind.HISTORY_SYNC, status: parent, subtitle: undefined, title: 'History refresh' }),
    activity('ethereum', { parent: id('refresh'), status: parent }),
    activity('0xaa', { parent: id('ethereum'), status: ActivityStatus.COMPLETE }),
    activity('0xbb', { parent: id('ethereum'), reason: 'rate limited', rerunnable: true, status: ActivityStatus.FAILED }),
  ];
}

describe('dockJobNode', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('while running', () => {
    /**
     * Collapsed at every level, the job's own fan-out included. The rolled-up row already says what
     * is running and how far along; unfolding eleven chains times four accounts into a 400px panel
     * to repeat it pushes every other job off the panel.
     */
    it('should render a job with its children collapsed', () => {
      const text = mountTree(running()).text();

      expect(text).toContain('History refresh');
      expect(text).not.toContain('ethereum');
    });

    it('should unfold one level per click', async () => {
      const wrapper = mountTree(running());

      const jobDisclosure = wrapper.find('[aria-expanded]');
      assert(jobDisclosure.exists(), 'the job rendered no disclosure');
      await jobDisclosure.trigger('click');

      expect(wrapper.text()).toContain('ethereum');
      expect(wrapper.text()).not.toContain('0xbb');

      const chainDisclosure = wrapper.findAll('[aria-expanded]').at(-1);
      assert(chainDisclosure, 'the chain rendered no disclosure');
      await chainDisclosure.trigger('click');

      expect(wrapper.text()).toContain('0xbb');
    });

    it('should tally a parent over its leaves, not over every activity in the subtree', () => {
      expect(mountTree(running()).text()).toContain('pending_task.steps::1, 2');
    });

    it('should offer a cancel control on a parent, whose cancel cascades to the subtree', async () => {
      const wrapper = mountTree(running());

      await wrapper.find('[data-testid=cancel-activity]').trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
    });

    it('should bubble a leaf cancel up to the panel', async () => {
      const wrapper = mountTree(running().slice(1), { depth: 1 });

      await wrapper.find('[aria-expanded]').trigger('click');
      await wrapper.findAll('[data-testid=cancel-activity]').at(-1)?.trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
    });

    it('should keep a running parent\'s children in start order and in place as they finish, with no cap hiding the ones still working', async () => {
      const done = ['0x1', '0x2', '0x3', '0x4', '0x5', '0x6'].map(name => activity(name, {
        parent: id('ethereum'),
        ...(name === '0x4' ? { reason: 'no key', status: ActivityStatus.FAILED } : { status: ActivityStatus.COMPLETE }),
      }));
      const wrapper = mountTree([activity('ethereum'), ...done, activity('0xrun', { parent: id('ethereum') })], { depth: 1 });

      await wrapper.find('[aria-expanded]').trigger('click');

      const labels = wrapper.findAll('[data-testid=dock-activity-row] .truncate').map(label => label.text());
      expect(labels.filter(label => label.startsWith('0x'))).toEqual(['0x1', '0x2', '0x3', '0x4', '0x5', '0x6', '0xrun']);
      expect(wrapper.find('[data-testid=dock-show-more-children]').exists()).toBe(false);
    });

    it('should put a job\'s sections and the sync hint in its row, aligned under the label', () => {
      const wrapper = mountTree([
        activity('refresh', { kind: ActivityKind.HISTORY_SYNC, subtitle: undefined, title: 'History refresh' }),
        activity('ethereum', { parent: id('refresh') }),
        activity('kraken', { id: makeActivityId(ActivityKind.EXCHANGE_EVENTS, 'kraken', 'main'), kind: ActivityKind.EXCHANGE_EVENTS, parent: id('refresh') }),
      ]);

      const row = wrapper.find('[data-testid=dock-activity-row]');
      expect(row.find('[data-testid=dock-job-breakdown]').exists()).toBe(true);
      expect(row.find('[data-testid=dock-sync-hint]').exists()).toBe(true);
    });

    it('should surface no failed leaves while the job is still running', () => {
      const tree = running();
      tree[3] = { ...tree[3], status: ActivityStatus.FAILED };

      expect(mountTree(tree).find('[data-testid=dock-failed-leaves]').exists()).toBe(false);
    });
  });

  describe('once settled', () => {
    it('should report a failure anywhere beneath a completed parent, not a success', () => {
      expect(mountTree(settled(ActivityStatus.COMPLETE)).find('[data-testid=activity-outcome]').attributes('aria-label')).toBe('pending_task.status.failed');
    });

    it('should keep reporting a cancelled parent as cancelled, whatever failed beneath it', () => {
      expect(mountTree(settled(ActivityStatus.CANCELLED)).find('[data-testid=activity-outcome]').attributes('aria-label')).toBe('pending_task.status.cancelled');
    });

    it('should list a failed leaf with its reason under the folded job, skipping the levels between', () => {
      const failedLeaves = mountTree(settled(ActivityStatus.COMPLETE)).find('[data-testid=dock-failed-leaves]');

      expect(failedLeaves.text()).toContain('0xbb');
      expect(failedLeaves.text()).toContain('rate limited');
      expect(failedLeaves.text()).not.toContain('0xaa');
      expect(failedLeaves.text()).not.toContain('ethereum');
    });

    it('should bubble a failed leaf\'s retry up to the panel', async () => {
      const wrapper = mountTree(settled(ActivityStatus.COMPLETE));

      await wrapper.find('[data-testid=retry-activity]').trigger('click');

      expect(wrapper.emitted('retry')?.[0]?.[0]).toMatchObject({ id: id('0xbb') });
    });

    it('should count the healthy leaves it hides, and open the job on request, each folded level surfacing its own', async () => {
      const wrapper = mountTree(settled(ActivityStatus.COMPLETE));

      const showAll = wrapper.find('[data-testid=dock-show-all]');
      expect(showAll.text()).toBe('task_dock.panel.show_all::1');

      await showAll.trigger('click');

      expect(wrapper.find('[aria-expanded]').attributes('aria-expanded')).toBe('true');
      expect(wrapper.text()).toContain('ethereum');
      expect(wrapper.findAll('[data-testid=retry-activity]')).toHaveLength(1);
    });

    it('should say how the job ended instead of a tally that is now always full, failures last and in the error colour', () => {
      const wrapper = mountTree(settled(ActivityStatus.COMPLETE));

      const parts = wrapper.findAll('[data-testid=dock-outcome-summary] > span');
      expect(parts.map(part => part.text())).toEqual(['task_dock.panel.outcome.done::1', 'task_dock.panel.outcome.failed::1']);
      expect(parts[0]?.classes().some(name => name.startsWith('before:'))).toBe(false);
      expect(wrapper.find('[data-testid=dock-outcome-failed]').classes()).toContain('text-rui-error');
      expect(wrapper.text()).not.toContain('pending_task.steps');
    });

    it('should keep the tally, with no outcome line, while the job runs', () => {
      const wrapper = mountTree(running());

      expect(wrapper.find('[data-testid=dock-outcome-summary]').exists()).toBe(false);
      expect(wrapper.text()).toContain('pending_task.steps::1, 2');
    });

    it('should list an unfolded job\'s failure first and fold skips that share a reason into one row', async () => {
      const wrapper = mountTree([
        activity('run', { kind: ActivityKind.BLOCKCHAIN_BALANCES, status: ActivityStatus.COMPLETE, subtitle: undefined, title: 'Blockchain balances' }),
        activity('eth', { parent: id('run'), status: ActivityStatus.COMPLETE }),
        activity('bch', { parent: id('run'), reason: 'no accounts', status: ActivityStatus.SKIPPED }),
        activity('eth2', { parent: id('run'), reason: 'unreachable', status: ActivityStatus.FAILED }),
        activity('ksm', { parent: id('run'), reason: 'no accounts', status: ActivityStatus.SKIPPED }),
      ]);

      await wrapper.find('[aria-expanded]').trigger('click');

      const rowLabels = wrapper.findAll('[data-testid=dock-activity-row] .truncate').map(label => label.text());
      expect(rowLabels.slice(1)).toEqual(['eth2', 'eth']);
      const group = wrapper.find('[data-testid=dock-skipped-group]');
      expect(group.text()).toContain('task_dock.panel.skipped_count::2');
      expect(group.text()).toContain('no accounts');
      expect(group.find('[data-testid=dock-skipped-names]').text()).toBe('bch, ksm');
    });

    it('should fold failed accounts that share a reason into one group with one reason and one retry for all', async () => {
      const wrapper = mountTree([
        activity('refresh', { kind: ActivityKind.HISTORY_SYNC, status: ActivityStatus.COMPLETE, subtitle: undefined, title: 'History refresh' }),
        activity('gnosis', { parent: id('refresh'), reason: 'no API key', status: ActivityStatus.FAILED }),
        activity('0xaa', { parent: id('gnosis'), reason: 'no API key', rerunnable: true, status: ActivityStatus.FAILED }),
        activity('0xbb', { parent: id('gnosis'), reason: 'no API key', rerunnable: true, status: ActivityStatus.FAILED }),
        activity('0xcc', { parent: id('gnosis'), reason: 'no API key', rerunnable: true, status: ActivityStatus.FAILED }),
      ]);

      const group = wrapper.find('[data-testid=dock-failed-group]');
      expect(group.find('[data-testid=dock-failed-group-reason]').text()).toBe('no API key');
      expect(group.findAll('[data-testid=activity-reason]')).toHaveLength(0);
      expect(group.text()).toContain('0xbb');

      await group.find('[data-testid=dock-failed-group-retry]').trigger('click');
      expect(wrapper.emitted('retry')).toHaveLength(3);
    });

    it('should not repeat on a parent the reason a child beneath it already states', async () => {
      const wrapper = mountTree([
        activity('gnosis', { reason: 'no API key', status: ActivityStatus.FAILED }),
        activity('0xaa', { parent: id('gnosis'), reason: 'no API key', status: ActivityStatus.FAILED }),
        activity('0xbb', { parent: id('gnosis'), status: ActivityStatus.COMPLETE }),
      ]);

      await wrapper.find('[aria-expanded]').trigger('click');

      expect(wrapper.findAll('[data-testid=activity-reason]').map(line => line.text())).toEqual(['no API key']);
    });

    it('should list five of a settled nested parent\'s children and the rest on request, but every child of a job', async () => {
      const accounts = ['0x1', '0x2', '0x3', '0x4', '0x5', '0x6', '0x7'].map(name => activity(name, { parent: id('ethereum'), status: ActivityStatus.COMPLETE }));
      const tree = [activity('ethereum', { status: ActivityStatus.COMPLETE }), ...accounts];

      const nested = mountTree(tree, { depth: 1 });
      await nested.find('[aria-expanded]').trigger('click');
      expect(nested.findAll('[data-testid=dock-activity-row]')).toHaveLength(6);

      await nested.find('[data-testid=dock-show-more-children]').trigger('click');
      expect(nested.findAll('[data-testid=dock-activity-row]')).toHaveLength(8);

      const job = mountTree(tree);
      await job.find('[aria-expanded]').trigger('click');
      expect(job.findAll('[data-testid=dock-activity-row]')).toHaveLength(8);
      expect(job.find('[data-testid=dock-show-more-children]').exists()).toBe(false);
    });

    it('should offer dismiss on the job row only', () => {
      expect(mountTree(settled(ActivityStatus.COMPLETE), { dismissible: true }).findAll('[data-testid=dismiss-activity]')).toHaveLength(1);
    });
  });
});
