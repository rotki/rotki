import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { assembleActivityModel } from '@/modules/task-center/core/model';
import {
  type Activity,
  type ActivityId,
  ActivityKind,
  type ActivityModel,
  ActivityPhase,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';
import { useTaskDock } from './use-task-dock';

const activities = ref<Activity[]>([]);

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): { isActive: ComputedRef<boolean>; model: ComputedRef<ActivityModel> } => {
    const model = computed<ActivityModel>(() => assembleActivityModel(get(activities), (key: string): string => key));
    return { isActive: computed<boolean>(() => get(model).overall.phase === ActivityPhase.WORKING), model };
  },
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

let scope: ReturnType<typeof effectScope> | undefined;

function dock(): ReturnType<typeof useTaskDock> {
  scope = effectScope();
  return scope.run(() => useTaskDock())!;
}

describe('useTaskDock', () => {
  beforeEach(() => {
    set(activities, []);
  });

  afterEach(() => {
    scope?.stop();
    scope = undefined;
  });

  describe('the primary job', () => {
    it('should name the long job even when a short job is listed ahead of it', () => {
      set(activities, [
        activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING),
        activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING),
        activity(ActivityKind.TX_SYNC, 'eth', ActivityStatus.RUNNING, refreshId),
      ]);

      const { otherJobs, primary, primarySteps } = dock();

      expect(get(primary)?.activity.kind).toBe(ActivityKind.HISTORY_SYNC);
      expect(get(otherJobs)).toBe(1);
      expect(get(primarySteps)).toEqual({ current: 0, total: 1 });
    });

    it('should pick between long kinds by the dock\'s own order, not the panel\'s', () => {
      set(activities, [
        activity(ActivityKind.PROTOCOL_CACHE, 'eth', ActivityStatus.RUNNING),
        activity(ActivityKind.PNL_REPORT, 'report', ActivityStatus.RUNNING),
      ]);

      expect(get(dock().primary)?.activity.kind).toBe(ActivityKind.PNL_REPORT);
    });

    it('should fall back to the first job, without a count, when only short jobs run', () => {
      set(activities, [activity(ActivityKind.BLOCKCHAIN_BALANCES, 'eth', ActivityStatus.RUNNING)]);

      const { isPrimaryLong, primary, primarySteps } = dock();

      expect(get(primary)?.activity.kind).toBe(ActivityKind.BLOCKCHAIN_BALANCES);
      expect(get(isPrimaryLong)).toBe(false);
      expect(get(primarySteps)).toBeUndefined();
    });

    it('should count a single long activity by the steps it reports, not as one leaf', () => {
      set(activities, [{ ...activity(ActivityKind.PRICES, 'latest', ActivityStatus.RUNNING), steps: { current: 1, total: 3 } }]);

      expect(get(dock().primarySteps)).toEqual({ current: 1, total: 3 });
    });

    it('should show no count for a single long activity that reports no steps', () => {
      set(activities, [activity(ActivityKind.PNL_REPORT, 'report', ActivityStatus.RUNNING)]);

      const { isPrimaryLong, primarySteps } = dock();

      expect(get(isPrimaryLong)).toBe(true);
      expect(get(primarySteps)).toBeUndefined();
    });

    it('should name nothing while everything is still queued, yet stay visible', () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.PENDING)]);

      const { primary, visible } = dock();

      expect(get(primary)).toBeUndefined();
      expect(get(visible)).toBe(true);
    });

    it('should hide once nothing is running or queued', () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.COMPLETE)]);

      expect(get(dock().visible)).toBe(false);
    });
  });

  describe('the panel', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should close once the work has been idle long enough', async () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING)]);
      const { modelExpanded } = dock();
      set(modelExpanded, true);

      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.COMPLETE)]);
      await nextTick();
      await vi.advanceTimersByTimeAsync(1000);

      expect(get(modelExpanded)).toBe(false);
    });

    it('should stay open while work is still active', async () => {
      const { modelExpanded } = dock();
      set(modelExpanded, true);

      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING)]);
      await nextTick();
      await vi.advanceTimersByTimeAsync(1000);

      expect(get(modelExpanded)).toBe(true);
    });
  });
});
