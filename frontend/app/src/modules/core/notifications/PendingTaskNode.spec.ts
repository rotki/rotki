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
  it('should render a job with its children expanded', () => {
    const text = createWrapper().text();

    expect(text).toContain('History refresh');
    expect(text).toContain('ethereum');
  });

  /** Eleven chains times four accounts is not something to unfold into a 400px drawer unasked. */
  it('should keep levels below the first collapsed until asked', async () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).not.toContain('0xbb');

    // The last disclosure is the chain's; the first is the job's, already open.
    const chainDisclosure = wrapper.findAll('[aria-expanded]').at(-1);
    assert(chainDisclosure, 'the chain rendered no disclosure');
    await chainDisclosure.trigger('click');

    expect(wrapper.text()).toContain('0xbb');
  });

  it('should show a parent its subtree tally in leaves', () => {
    // One of the two accounts is done: the job is 1 of 2, not 1 of 3 activities.
    expect(createWrapper().text()).toContain('pending_task.steps::1, 2');
  });

  /**
   * ⚠️ Cancelling a parent today settles its row and stops nothing — the handle aborts a backend
   * task id an umbrella never has, and cancel does not walk descendants. The control comes back
   * when cancellation cascades.
   */
  it('should offer no cancel control on a parent', () => {
    expect(createWrapper().findAll('[data-testid=cancel-activity]')).toHaveLength(0);
  });

  it('should bubble a leaf cancel up to the panel', async () => {
    const { children, root } = tree();
    const chain = children.get(root.id)?.[0];
    const wrapper = mount(PendingTaskNode, { props: { activity: chain!, children, depth: 1, now: NOW } });

    // Mounted below the first level, so it starts collapsed; its accounts carry the control.
    await wrapper.find('[aria-expanded]').trigger('click');
    await wrapper.find('[data-testid=cancel-activity]').trigger('click');

    expect(wrapper.emitted('cancel')).toHaveLength(1);
  });
});
