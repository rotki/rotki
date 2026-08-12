import { describe, expect, it } from 'vitest';
import { buildTree, someInSubtree, subtreeProgress, subtreeSteps } from './tree';
import { type Activity, type ActivityId, ActivityKind, ActivitySourceType, ActivityStatus, makeActivityId } from './types';

function activity(id: string, status: ActivityStatus, parent?: string, startedAt?: number): Activity {
  return {
    cancellable: false,
    id: makeActivityId(ActivityKind.TX_SYNC, id),
    kind: ActivityKind.TX_SYNC,
    parent: parent === undefined ? undefined : makeActivityId(ActivityKind.TX_SYNC, parent),
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    startedAt,
    status,
    title: id,
  };
}

function id(value: string): ActivityId {
  return makeActivityId(ActivityKind.TX_SYNC, value);
}

/** Insertion order, so a tree is never accidentally correct because the input was already sorted. */
const byId = (a: Activity, b: Activity): number => a.id.localeCompare(b.id);

describe('buildTree', () => {
  it('should nest children under their declared parent', () => {
    const { children, roots } = buildTree([
      activity('umbrella', ActivityStatus.RUNNING),
      activity('eth', ActivityStatus.RUNNING, 'umbrella'),
      activity('eth-a', ActivityStatus.RUNNING, 'eth'),
    ], byId);

    expect(roots.map(root => root.id)).toEqual([id('umbrella')]);
    expect(children.get(id('umbrella'))?.map(child => child.id)).toEqual([id('eth')]);
    expect(children.get(id('eth'))?.map(child => child.id)).toEqual([id('eth-a')]);
  });

  /**
   * `clearTerminal` prunes settled records, so a parent can legitimately vanish while its children
   * still run. Dropping those children would hide live work entirely — the panel would show
   * nothing while the app kept querying.
   */
  it('should treat an activity whose parent is absent as a root', () => {
    const { roots } = buildTree([activity('orphan', ActivityStatus.RUNNING, 'gone')], byId);

    expect(roots.map(root => root.id)).toEqual([id('orphan')]);
  });

  it('should order siblings by start time, with unstarted ones last', () => {
    const { children } = buildTree([
      activity('parent', ActivityStatus.RUNNING),
      activity('queued', ActivityStatus.PENDING, 'parent'),
      activity('second', ActivityStatus.RUNNING, 'parent', 200),
      activity('first', ActivityStatus.RUNNING, 'parent', 100),
    ], byId);

    expect(children.get(id('parent'))?.map(child => child.id)).toEqual([
      id('first'),
      id('second'),
      id('queued'),
    ]);
  });

  it('should leave a parent with no children out of the map', () => {
    const { children, roots } = buildTree([activity('lonely', ActivityStatus.RUNNING)], byId);

    expect(roots).toHaveLength(1);
    expect(children.size).toBe(0);
  });
});

describe('subtreeSteps', () => {
  /**
   * Leaves only. Counting rows instead would let every intermediate node inflate the denominator:
   * the tree below is 2 accounts of work, not 4 activities of it.
   */
  it('should count leaves, not rows', () => {
    const activities = [
      activity('umbrella', ActivityStatus.RUNNING),
      activity('eth', ActivityStatus.RUNNING, 'umbrella'),
      activity('eth-a', ActivityStatus.COMPLETE, 'eth'),
      activity('eth-b', ActivityStatus.RUNNING, 'eth'),
    ];
    const { children, roots } = buildTree(activities, byId);

    expect(subtreeSteps(children, roots[0])).toEqual({ current: 1, total: 2 });
  });

  it('should count a childless activity as one step', () => {
    const { children, roots } = buildTree([activity('solo', ActivityStatus.RUNNING)], byId);

    expect(subtreeSteps(children, roots[0])).toEqual({ current: 0, total: 1 });
  });

  /**
   * The rollup counts both as done on purpose (`projection.ts`): no further progress is coming, so
   * a bar that excluded them would stall. The chip on the row is what tells the user they were not
   * successes.
   */
  it('should count failed and skipped leaves as done', () => {
    const { children, roots } = buildTree([
      activity('parent', ActivityStatus.RUNNING),
      activity('failed', ActivityStatus.FAILED, 'parent'),
      activity('skipped', ActivityStatus.SKIPPED, 'parent'),
      activity('running', ActivityStatus.RUNNING, 'parent'),
    ], byId);

    expect(subtreeSteps(children, roots[0])).toEqual({ current: 2, total: 3 });
  });

  it('should not hang on a parent cycle', () => {
    const a = activity('a', ActivityStatus.RUNNING, 'b');
    const b = activity('b', ActivityStatus.RUNNING, 'a');
    const { children } = buildTree([a, b], byId);

    expect(subtreeSteps(children, a).total).toBeLessThanOrEqual(2);
  });
});

describe('someInSubtree', () => {
  const isRunning = (item: Activity): boolean => item.status === ActivityStatus.RUNNING;

  it('should find a running descendant under a queued root', () => {
    const { children, roots } = buildTree([
      activity('parent', ActivityStatus.PENDING),
      activity('child', ActivityStatus.RUNNING, 'parent'),
    ], byId);

    expect(someInSubtree(children, roots[0], isRunning)).toBe(true);
  });

  it('should be false when the whole subtree is queued', () => {
    const { children, roots } = buildTree([
      activity('parent', ActivityStatus.PENDING),
      activity('child', ActivityStatus.PENDING, 'parent'),
    ], byId);

    expect(someInSubtree(children, roots[0], isRunning)).toBe(false);
  });
});

describe('subtreeProgress', () => {
  function withPercentage(base: Activity, percentage: number): Activity {
    return { ...base, percentage };
  }

  /**
   * The bug this exists for: a job that is a single running leaf has no settled leaves, so a tally
   * of whole steps can only ever say `0 of 1`. The leaf's own percentage is the one number it has,
   * and the header used to throw it away and render a ring pinned at 0 above a row showing 45%.
   */
  it('should give a leaf fractional credit for its own progress', () => {
    const root = withPercentage(activity('prices', ActivityStatus.RUNNING), 45);
    const { children } = buildTree([root], byId);

    expect(subtreeProgress(children, root)).toBe(45);
    expect(subtreeSteps(children, root)).toEqual({ current: 0, total: 1 });
  });

  it('should count a settled leaf as whole regardless of its percentage', () => {
    const root = withPercentage(activity('prices', ActivityStatus.COMPLETE), 20);
    const { children } = buildTree([root], byId);

    expect(subtreeProgress(children, root)).toBe(100);
  });

  /** Unknown work is unfinished work: it drags the mean down rather than leaving the denominator. */
  it('should count an unquantifiable leaf as zero without dropping it', () => {
    const activities = [
      activity('umbrella', ActivityStatus.RUNNING),
      withPercentage(activity('eth', ActivityStatus.COMPLETE, 'umbrella'), 100),
      activity('gno', ActivityStatus.RUNNING, 'umbrella'),
    ];
    const { children, roots } = buildTree(activities, byId);

    expect(subtreeProgress(children, roots[0])).toBe(50);
  });

  it('should say so when nothing in the subtree can be quantified', () => {
    const activities = [
      activity('umbrella', ActivityStatus.RUNNING),
      activity('eth', ActivityStatus.RUNNING, 'umbrella'),
    ];
    const { children, roots } = buildTree(activities, byId);

    expect(subtreeProgress(children, roots[0])).toBe(-1);
  });

  it('should average the leaves of a deep tree, not its rows', () => {
    const activities = [
      activity('umbrella', ActivityStatus.RUNNING),
      activity('eth', ActivityStatus.RUNNING, 'umbrella'),
      activity('eth-a', ActivityStatus.COMPLETE, 'eth'),
      withPercentage(activity('eth-b', ActivityStatus.RUNNING, 'eth'), 50),
    ];
    const { children, roots } = buildTree(activities, byId);

    // Two leaves: one whole, one half. The two intermediate rows count for nothing.
    expect(subtreeProgress(children, roots[0])).toBe(75);
  });
});
