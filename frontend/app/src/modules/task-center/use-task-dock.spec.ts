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
import { DockState } from './dock-state';
import { useTaskDock } from './use-task-dock';

const activities = ref<Activity[]>([]);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<boolean> => ref<boolean>(false),
}));

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

    it('should hide for a clean run that had already settled before the dock saw it running', () => {
      set(activities, refresh(ActivityStatus.COMPLETE));

      expect(get(dock().visible)).toBe(false);
    });

    it('should report a failure beneath a job that settled before the dock mounted, as one started during login', () => {
      set(activities, refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));

      const { failed, state } = dock();

      expect(get(state)).toBe(DockState.FAILED);
      expect(get(failed).map(root => root.id)).toEqual([refreshId]);
    });
  });

  describe('the outcome of a run', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should keep reporting a clean run, however long it is left, until it is dismissed', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, dismissedFailure, finished, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE));
      await vi.advanceTimersByTimeAsync(60000);

      expect(get(state)).toBe(DockState.DONE);
      expect(get(finished).map(root => root.id)).toEqual([refreshId]);

      acknowledge(refreshId);

      expect(get(state)).toBe(DockState.DISMISSED);
      expect(get(dismissedFailure)).toBe(false);
    });

    it('should replace a clean run, dismissed or not, once a new run starts', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, dismissed, finished, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE));
      acknowledge(refreshId);
      await transition([...refresh(ActivityStatus.COMPLETE), report(ActivityStatus.RUNNING)]);
      await transition([...refresh(ActivityStatus.COMPLETE), report(ActivityStatus.COMPLETE)]);

      expect(get(state)).toBe(DockState.DONE);
      expect(get(finished).map(root => root.kind)).toEqual([ActivityKind.PNL_REPORT]);
      expect(get(dismissed)).toEqual([]);
    });

    it('should report a failure anywhere in a job\'s subtree until acknowledged, then keep it as dismissed', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, dismissed, failed, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      await vi.advanceTimersByTimeAsync(60000);

      expect(get(state)).toBe(DockState.FAILED);
      expect(get(failed).map(root => root.id)).toEqual([refreshId]);

      acknowledge(refreshId);

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

    it('should report a dismissed failure afresh as done once the job reruns cleanly', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, dismissed, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      acknowledge(refreshId);
      await transition(refresh(ActivityStatus.RUNNING));
      await transition(refresh(ActivityStatus.COMPLETE));

      expect(get(state)).toBe(DockState.DONE);
      expect(get(dismissed)).toEqual([]);
    });

    it('should keep a dismissed failure through another job\'s clean run, and return to it once that is dismissed', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      const reportId = makeActivityId(ActivityKind.PNL_REPORT, 'report');
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, dismissedFailure, state } = dock();

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      acknowledge(refreshId);
      await transition([...refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED), report(ActivityStatus.RUNNING)]);
      await transition([...refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED), report(ActivityStatus.COMPLETE)]);

      expect(get(state)).toBe(DockState.DONE);

      acknowledge(reportId);

      expect(get(state)).toBe(DockState.DISMISSED);
      expect(get(dismissedFailure)).toBe(true);
    });

    async function dismissedFailure(): Promise<ReturnType<typeof useTaskDock>> {
      set(activities, refresh(ActivityStatus.RUNNING));
      const docked = dock();
      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.FAILED));
      docked.acknowledge(refreshId);
      await nextTick();
      return docked;
    }

    it('should go away once everything is dismissed and it sits collapsed and untouched long enough, and not before', async () => {
      const { dismissed, state } = await dismissedFailure();

      await vi.advanceTimersByTimeAsync(9000);
      expect(get(state)).toBe(DockState.DISMISSED);

      await vi.advanceTimersByTimeAsync(1000);
      expect(get(state)).toBeUndefined();
      expect(get(dismissed)).toEqual([]);
    });

    it('should hold off going away while the dismissed dock is hovered, and wait the full time again once it is left', async () => {
      const { holdInteraction, state } = await dismissedFailure();

      await vi.advanceTimersByTimeAsync(9000);
      holdInteraction(true);
      await nextTick();
      await vi.advanceTimersByTimeAsync(60000);
      expect(get(state)).toBe(DockState.DISMISSED);

      holdInteraction(false);
      await nextTick();
      await vi.advanceTimersByTimeAsync(9000);
      expect(get(state)).toBe(DockState.DISMISSED);

      await vi.advanceTimersByTimeAsync(1000);
      expect(get(state)).toBeUndefined();
    });

    it('should never go away while the dismissed dock\'s panel is open', async () => {
      const { modelExpanded, state } = await dismissedFailure();

      set(modelExpanded, true);
      await nextTick();
      await vi.advanceTimersByTimeAsync(60000);

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

    it('should close once the work goes idle with nothing to report, as after a cancelled run', async () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING)]);
      const { modelExpanded } = dock();
      set(modelExpanded, true);

      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.CANCELLED)]);
      await nextTick();
      await vi.advanceTimersByTimeAsync(1000);

      expect(get(modelExpanded)).toBe(false);
    });

    it('should stay open over a clean run\'s outcome once the work goes idle, however long it is left', async () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING)]);
      const { modelExpanded } = dock();
      set(modelExpanded, true);

      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.COMPLETE)]);
      await nextTick();
      await vi.advanceTimersByTimeAsync(60000);

      expect(get(modelExpanded)).toBe(true);
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
