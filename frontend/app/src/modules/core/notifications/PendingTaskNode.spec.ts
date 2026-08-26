import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, describe, expect, it } from 'vitest';
import PendingTaskNode from '@/modules/core/notifications/PendingTaskNode.vue';
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

/**
 * A three-level tree, the shape a history refresh actually declares: one job, a chain under it,
 * two accounts under the chain.
 */
function tree(): { children: ReadonlyMap<ActivityId, Activity[]>; root: Activity } {
  const activities = [
    activity('refresh', { kind: ActivityKind.HISTORY_SYNC, subtitle: undefined, title: 'History refresh' }),
    activity('ethereum', { parent: id('refresh') }),
    activity('0xaa', { parent: id('ethereum'), status: ActivityStatus.COMPLETE }),
    activity('0xbb', { parent: id('ethereum') }),
  ];
  const { children, roots } = buildTree(activities, (a, b) => a.id.localeCompare(b.id));
  return { children, root: roots[0] };
}

function createWrapper(): VueWrapper {
  const { children, root } = tree();
  return mount(PendingTaskNode, { props: { activity: root, children, now: NOW } });
}

describe('pendingTaskNode', () => {
  /**
   * Collapsed at every level, the job's own fan-out included. The rolled-up row already says what
   * is running and how far along; unfolding eleven chains times four accounts into a 400px drawer
   * to repeat it pushes every other job off the panel.
   */
  it('should render a job with its children collapsed', () => {
    const text = createWrapper().text();

    expect(text).toContain('History refresh');
    expect(text).not.toContain('ethereum');
  });

  it('should unfold one level per click', async () => {
    const wrapper = createWrapper();

    const jobDisclosure = wrapper.find('[aria-expanded]');
    assert(jobDisclosure.exists(), 'the job rendered no disclosure');
    await jobDisclosure.trigger('click');

    // The chain is now visible, but its own accounts are not: one click, one level.
    expect(wrapper.text()).toContain('ethereum');
    expect(wrapper.text()).not.toContain('0xbb');

    const chainDisclosure = wrapper.findAll('[aria-expanded]').at(-1);
    assert(chainDisclosure, 'the chain rendered no disclosure');
    await chainDisclosure.trigger('click');

    expect(wrapper.text()).toContain('0xbb');
  });

  it('should show a parent its subtree tally in leaves', () => {
    // One of the two accounts is done: the job is 1 of 2, not 1 of 3 activities.
    expect(createWrapper().text()).toContain('pending_task.steps::1, 2');
  });

  it('should offer a cancel control on a parent, whose cancel cascades to the subtree', async () => {
    const wrapper = createWrapper();
    const control = wrapper.find('[data-testid=cancel-activity]');
    expect(control.exists()).toBe(true);

    await control.trigger('click');

    expect(wrapper.emitted('cancel')).toHaveLength(1);
  });

  it('should bubble a leaf cancel up to the panel', async () => {
    const { children, root } = tree();
    const chain = children.get(root.id)?.[0];
    const wrapper = mount(PendingTaskNode, { props: { activity: chain!, children, depth: 1, now: NOW } });

    // Starts collapsed like every parent; its accounts carry the control once it is open.
    await wrapper.find('[aria-expanded]').trigger('click');
    await wrapper.find('[data-testid=cancel-activity]').trigger('click');

    expect(wrapper.emitted('cancel')).toHaveLength(1);
  });
});
