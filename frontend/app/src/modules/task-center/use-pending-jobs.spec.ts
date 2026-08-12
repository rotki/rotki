import { beforeEach, describe, expect, it, vi } from 'vitest';
import { assembleActivityModel } from './core/model';
import {
  type Activity,
  type ActivityKind,
  type ActivityModel,
  ActivitySourceType,
  type ActivityStatus,
  ActivityKind as Kind,
  makeActivityId,
  ActivityStatus as Status,
} from './core/types';
import { usePendingJobs } from './use-pending-jobs';

const activities = ref<Activity[]>([]);

vi.mock('./use-task-center', () => ({
  useTaskCenter: (): { model: ComputedRef<ActivityModel> } => ({
    model: computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key)),
  }),
}));

function activity(
  id: string,
  status: ActivityStatus,
  options: { kind?: ActivityKind; parent?: string; percentage?: number } = {},
): Activity {
  const { kind = Kind.TX_SYNC, parent, percentage = -1 } = options;
  return {
    cancellable: false,
    id: makeActivityId(kind, id),
    kind,
    parent: parent === undefined ? undefined : makeActivityId(Kind.HISTORY_SYNC, parent),
    percentage,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: id,
  };
}

function umbrella(status: ActivityStatus): Activity {
  return {
    cancellable: false,
    id: makeActivityId(Kind.HISTORY_SYNC, 'refresh'),
    kind: Kind.HISTORY_SYNC,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    title: 'History refresh',
  };
}

describe('usePendingJobs', () => {
  beforeEach(() => {
    set(activities, []);
  });

  it('should list one job for a whole subtree, not one per activity', () => {
    set(activities, [
      umbrella(Status.RUNNING),
      activity('ethereum', Status.RUNNING, { parent: 'refresh' }),
      activity('gnosis', Status.PENDING, { parent: 'refresh' }),
    ]);

    const { jobs } = usePendingJobs();

    expect(get(jobs)).toHaveLength(1);
    expect(get(jobs)[0].activity.title).toBe('History refresh');
  });

  /**
   * The old panel listed RUNNING activities, so a job whose only running work was one leaf
   * disappeared the moment that leaf settled, even with queued siblings behind it. Listing by
   * subtree keeps the job up for as long as any of it is actually moving.
   */
  it('should list a queued root that has a running descendant', () => {
    set(activities, [
      umbrella(Status.PENDING),
      activity('ethereum', Status.RUNNING, { parent: 'refresh' }),
    ]);

    expect(get(usePendingJobs().jobs)).toHaveLength(1);
  });

  it('should list nothing while the whole tree is still queued', () => {
    set(activities, [
      umbrella(Status.PENDING),
      activity('ethereum', Status.PENDING, { parent: 'refresh' }),
    ]);

    expect(get(usePendingJobs().jobs)).toEqual([]);
  });

  it('should count steps in leaves across every live job', () => {
    set(activities, [
      umbrella(Status.RUNNING),
      activity('ethereum', Status.COMPLETE, { parent: 'refresh' }),
      activity('gnosis', Status.RUNNING, { parent: 'refresh' }),
      activity('prices', Status.RUNNING, { kind: Kind.PRICES }),
    ]);

    const { jobs, percentage, steps } = usePendingJobs();

    expect(get(jobs)).toHaveLength(2);
    // Two leaves under the umbrella, one of them done, plus the standalone price fetch.
    expect(get(steps)).toEqual({ current: 1, total: 3 });
    expect(get(percentage)).toBe(33);
  });

  it('should expose the tree so the row component can walk it', () => {
    set(activities, [
      umbrella(Status.RUNNING),
      activity('ethereum', Status.RUNNING, { parent: 'refresh' }),
    ]);

    const { children, jobs } = usePendingJobs();

    expect(get(children).get(get(jobs)[0].activity.id)?.map(child => child.title)).toEqual(['ethereum']);
  });

  it('should report an indeterminate percentage when nothing is in flight', () => {
    expect(get(usePendingJobs().percentage)).toBe(-1);
  });
});
