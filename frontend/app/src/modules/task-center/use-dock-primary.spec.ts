import { describe, expect, it, vi } from 'vitest';
import { assembleActivityModel } from '@/modules/task-center/core/model';
import {
  type Activity,
  type ActivityId,
  ActivityKind,
  type ActivityModel,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';
import { useDockPrimary } from './use-dock-primary';
import { usePendingJobs } from './use-pending-jobs';

const activities = ref<Activity[]>([]);

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { model: ComputedRef<ActivityModel> } => ({
    model: computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key)),
  }),
}));

function activity(kind: ActivityKind, name: string, status: ActivityStatus, parent?: ActivityId): Activity {
  return {
    cancellable: true,
    id: makeActivityId(kind, name),
    kind,
    parent,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status,
    subtitle: name,
    title: `${kind} title`,
  };
}

const refreshId = makeActivityId(ActivityKind.HISTORY_SYNC, 'refresh');

function primaryOf(list: Activity[]): ReturnType<typeof useDockPrimary> {
  set(activities, list);
  const { children, jobs } = usePendingJobs();
  return useDockPrimary(jobs, children);
}

describe('useDockPrimary', () => {
  it('should name the long job even when a short job is listed ahead of it', () => {
    const { otherJobs, primary, primarySteps } = primaryOf([
      activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING),
      activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING),
      activity(ActivityKind.TX_SYNC, 'eth', ActivityStatus.RUNNING, refreshId),
    ]);

    expect(get(primary)?.activity.kind).toBe(ActivityKind.HISTORY_SYNC);
    expect(get(otherJobs)).toBe(1);
    expect(get(primarySteps)).toEqual({ current: 0, total: 1 });
  });

  it('should never name upkeep work ahead of a ranked job', () => {
    const { primary } = primaryOf([
      activity(ActivityKind.PRICES, 'latest', ActivityStatus.RUNNING),
      activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING),
    ]);

    expect(get(primary)?.activity.kind).toBe(ActivityKind.BLOCKCHAIN_BALANCES);
  });

  it('should fall back to the first job, neither ranked nor counted, when only upkeep runs', () => {
    const { isPrimaryRanked, primary, primarySteps } = primaryOf([
      { ...activity(ActivityKind.PRICES, 'latest', ActivityStatus.RUNNING), steps: { current: 1, total: 3 } },
    ]);

    expect(get(primary)?.activity.kind).toBe(ActivityKind.PRICES);
    expect(get(isPrimaryRanked)).toBe(false);
    expect(get(primarySteps)).toBeUndefined();
  });

  it('should count a single ranked activity by the steps it reports, not as one leaf', () => {
    const { primarySteps } = primaryOf([
      { ...activity(ActivityKind.HISTORICAL_BALANCES, 'range', ActivityStatus.RUNNING), steps: { current: 1, total: 3 } },
    ]);

    expect(get(primarySteps)).toEqual({ current: 1, total: 3 });
  });

  it('should show no count for a single ranked activity that reports no steps', () => {
    const { isPrimaryRanked, primarySteps } = primaryOf([activity(ActivityKind.PNL_REPORT, 'report', ActivityStatus.RUNNING)]);

    expect(get(isPrimaryRanked)).toBe(true);
    expect(get(primarySteps)).toBeUndefined();
  });

  it('should name nothing while everything is still queued', () => {
    const { otherJobs, primary } = primaryOf([activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.PENDING)]);

    expect(get(primary)).toBeUndefined();
    expect(get(otherJobs)).toBe(0);
  });
});
