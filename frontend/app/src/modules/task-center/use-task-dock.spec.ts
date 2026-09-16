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
import { DockState, useTaskDock } from './use-task-dock';

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

/** A history refresh with one chain under it, each in the given status. */
function refresh(status: ActivityStatus, chain: ActivityStatus = status): Activity[] {
  return [
    activity(ActivityKind.HISTORY_SYNC, 'refresh', status),
    activity(ActivityKind.TX_SYNC, 'ethereum', chain, refreshId),
  ];
}

let scope: ReturnType<typeof effectScope> | undefined;

function dock(): ReturnType<typeof useTaskDock> {
  scope = effectScope();
  return scope.run(() => useTaskDock())!;
}

async function transition(next: Activity[]): Promise<void> {
  set(activities, next);
  await nextTick();
}

describe('useTaskDock', () => {
  beforeEach(() => {
    set(activities, []);
  });

  afterEach(() => {
    scope?.stop();
    scope = undefined;
  });

  describe('visibility', () => {
    it('should be working and visible while everything is still queued', () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.PENDING)]);

      const { state, visible } = dock();

      expect(get(state)).toBe(DockState.WORKING);
      expect(get(visible)).toBe(true);
    });

    it('should hide for work that had already settled before the dock saw it running', () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.FAILED)]);

      expect(get(dock().visible)).toBe(false);
    });
  });

  describe('the outcome of a run', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should peek a summary of a clean run, then hide', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { finished, state, visible } = dock();

      await transition(refresh(ActivityStatus.COMPLETE));

      expect(get(state)).toBe(DockState.DONE);
      expect(get(finished).map(root => root.id)).toEqual([refreshId]);

      await vi.advanceTimersByTimeAsync(6000);

      expect(get(visible)).toBe(false);
    });

    it('should keep the summary while held, and hide once released', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { holdPeek, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE));
      holdPeek(true);
      await vi.advanceTimersByTimeAsync(20000);

      expect(get(state)).toBe(DockState.DONE);

      holdPeek(false);
      await vi.advanceTimersByTimeAsync(6000);

      expect(get(state)).toBeUndefined();
    });

    it('should report a failure anywhere in a job\'s subtree until acknowledged, then keep it as dismissed', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, dismissed, failed, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      await vi.advanceTimersByTimeAsync(60000);

      expect(get(state)).toBe(DockState.FAILED);
      expect(get(failed).map(root => root.id)).toEqual([refreshId]);

      acknowledge(refreshId);
      await vi.advanceTimersByTimeAsync(60000);

      expect(get(state)).toBe(DockState.DISMISSED);
      expect(get(failed)).toEqual([]);
      expect(get(dismissed).map(root => root.id)).toEqual([refreshId]);
    });

    it('should dismiss only the acknowledged job, keeping the panel open over the other failure', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      set(activities, [...refresh(ActivityStatus.RUNNING), report(ActivityStatus.RUNNING)]);
      const { acknowledge, failed, modelExpanded, state } = dock();
      set(modelExpanded, true);

      await transition([...refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED), report(ActivityStatus.FAILED)]);
      acknowledge(refreshId);

      expect(get(state)).toBe(DockState.FAILED);
      expect(get(failed).map(root => root.kind)).toEqual([ActivityKind.PNL_REPORT]);
      expect(get(modelExpanded)).toBe(true);

      acknowledge(makeActivityId(ActivityKind.PNL_REPORT, 'report'));

      expect(get(state)).toBe(DockState.DISMISSED);
      expect(get(modelExpanded)).toBe(false);
    });

    it('should clear a dismissed failure once the job reruns cleanly', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      acknowledge(refreshId);
      await transition(refresh(ActivityStatus.RUNNING));
      await transition(refresh(ActivityStatus.COMPLETE));
      await vi.advanceTimersByTimeAsync(6000);

      expect(get(state)).toBeUndefined();
    });

    it('should return to the dismissed failure after peeking another job\'s clean run', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      acknowledge(refreshId);
      await transition([...refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED), report(ActivityStatus.RUNNING)]);
      await transition([...refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED), report(ActivityStatus.COMPLETE)]);

      expect(get(state)).toBe(DockState.DONE);

      await vi.advanceTimersByTimeAsync(6000);

      expect(get(state)).toBe(DockState.DISMISSED);
    });

    it('should clear a failure on its own once the job is rerun', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      await transition(refresh(ActivityStatus.RUNNING));

      expect(get(state)).toBe(DockState.WORKING);

      await transition(refresh(ActivityStatus.COMPLETE));

      expect(get(state)).toBe(DockState.DONE);
    });

    it('should report an acknowledged job again when a later run of it fails', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      acknowledge(refreshId);
      await transition(refresh(ActivityStatus.RUNNING));
      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));

      expect(get(state)).toBe(DockState.FAILED);
    });

    it('should report nothing for a run the user cancelled', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { visible } = dock();

      await transition(refresh(ActivityStatus.CANCELLED));

      expect(get(visible)).toBe(false);
    });

    it('should summarize only the latest run, not the jobs of the one before', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      const prices = (status: ActivityStatus): Activity => activity(ActivityKind.PRICES, 'latest', status);
      set(activities, [report(ActivityStatus.RUNNING)]);
      const { finished } = dock();

      await transition([report(ActivityStatus.COMPLETE)]);
      await transition([report(ActivityStatus.COMPLETE), prices(ActivityStatus.RUNNING)]);
      await transition([report(ActivityStatus.COMPLETE), prices(ActivityStatus.COMPLETE)]);

      expect(get(finished).map(root => root.kind)).toEqual([ActivityKind.PRICES]);
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

    it('should stay open over failures once the work goes idle', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { modelExpanded } = dock();
      set(modelExpanded, true);

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      await vi.advanceTimersByTimeAsync(1000);

      expect(get(modelExpanded)).toBe(true);
    });
  });
});
