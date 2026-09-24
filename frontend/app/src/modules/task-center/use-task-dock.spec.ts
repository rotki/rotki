import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { type ActivityModel, assembleActivityModel } from '@/modules/task-center/core/model';
import {
  type Activity,
  type ActivityId,
  ActivityKind,
  ActivityPhase,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';
import { DockState } from './dock-state';
import { useTaskDock } from './use-task-dock';

const activities = ref<Activity[]>([]);
const showSummary = ref<boolean>(false);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<boolean> => showSummary,
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

/** Marks the refresh's chain as a skip that asked for attention. */
function attentionOnChain(list: Activity[]): Activity[] {
  return list.map(item => (item.parent === refreshId ? { ...item, attention: true } : item));
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

/** Leaves the work idle long enough for its batch to end; the next run starts a new one. */
async function endBatch(): Promise<void> {
  await vi.advanceTimersByTimeAsync(1000);
}

describe('useTaskDock', () => {
  beforeEach(() => {
    set(activities, []);
    set(showSummary, false);
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
      await endBatch();
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

    it('should hold a skip that asked for attention apart from a clean run, and pass a routine skip as one', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { failed, finished, flagged, state } = dock();

      await transition(attentionOnChain(refresh(ActivityStatus.COMPLETE, ActivityStatus.SKIPPED)));

      expect(get(state)).toBe(DockState.ATTENTION);
      expect(get(flagged).map(root => root.id)).toEqual([refreshId]);
      expect(get(finished)).toEqual([]);
      expect(get(failed)).toEqual([]);

      await transition(refresh(ActivityStatus.COMPLETE, ActivityStatus.SKIPPED));

      expect(get(state)).toBe(DockState.DONE);
      expect(get(flagged)).toEqual([]);
    });

    it('should keep a skip that asked for attention through the next run, as a failure is kept', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      set(activities, refresh(ActivityStatus.RUNNING));
      const { finished, flagged, state } = dock();

      const held = attentionOnChain(refresh(ActivityStatus.COMPLETE, ActivityStatus.SKIPPED));
      await transition(held);
      await endBatch();
      await transition([...held, report(ActivityStatus.RUNNING)]);
      await transition([...held, report(ActivityStatus.COMPLETE)]);

      expect(get(state)).toBe(DockState.ATTENTION);
      expect(get(flagged).map(root => root.id)).toEqual([refreshId]);
      expect(get(finished).map(root => root.kind)).toEqual([ActivityKind.PNL_REPORT]);
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

    it('should keep a run the user cancelled as an outcome until it is dismissed', async () => {
      set(activities, refresh(ActivityStatus.RUNNING));
      const { acknowledge, finished, state } = dock();

      await transition(refresh(ActivityStatus.CANCELLED));
      await vi.advanceTimersByTimeAsync(60000);

      expect(get(state)).toBe(DockState.DONE);
      expect(get(finished).map(root => root.id)).toEqual([refreshId]);

      acknowledge(refreshId);

      expect(get(state)).toBe(DockState.DISMISSED);
    });

    it('should summarize only the latest run, not the jobs of the one before', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      const prices = (status: ActivityStatus): Activity => activity(ActivityKind.PRICES, 'latest', status);
      set(activities, [report(ActivityStatus.RUNNING)]);
      const { finished } = dock();

      await transition([report(ActivityStatus.COMPLETE)]);
      await endBatch();
      await transition([report(ActivityStatus.COMPLETE), prices(ActivityStatus.RUNNING)]);
      await transition([report(ActivityStatus.COMPLETE), prices(ActivityStatus.COMPLETE)]);

      expect(get(finished).map(root => root.kind)).toEqual([ActivityKind.PRICES]);
    });

    it('should keep a run\'s outcome when more work starts within a second of it, as the same batch', async () => {
      const report = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'report', status);
      const prices = (status: ActivityStatus): Activity => activity(ActivityKind.PRICES, 'latest', status);
      set(activities, [report(ActivityStatus.RUNNING)]);
      const { finished } = dock();

      await transition([report(ActivityStatus.COMPLETE)]);
      await vi.advanceTimersByTimeAsync(50);
      await transition([report(ActivityStatus.COMPLETE), prices(ActivityStatus.RUNNING)]);
      await transition([report(ActivityStatus.COMPLETE), prices(ActivityStatus.COMPLETE)]);

      expect(get(finished).map(root => root.kind)).toHaveLength(2);
      expect(get(finished).map(root => root.kind)).toEqual(expect.arrayContaining([ActivityKind.PNL_REPORT, ActivityKind.PRICES]));
    });
  });

  describe('the panel', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should close once the work goes idle with nothing to report, as when it leaves the ledger', async () => {
      set(activities, [activity(ActivityKind.HISTORY_SYNC, 'refresh', ActivityStatus.RUNNING)]);
      const { modelExpanded } = dock();
      set(modelExpanded, true);

      set(activities, []);
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

    it('should summarize work that pauses for a moment between stages once, after the last stage', async () => {
      const balances = (status: ActivityStatus): Activity => activity(ActivityKind.PNL_REPORT, 'balances', status);
      const prices = (status: ActivityStatus): Activity => activity(ActivityKind.PRICES, 'latest', status);
      set(showSummary, true);
      set(activities, [balances(ActivityStatus.RUNNING)]);
      const { modelExpanded } = dock();

      await transition([balances(ActivityStatus.COMPLETE)]);
      await vi.advanceTimersByTimeAsync(50);
      expect(get(modelExpanded)).toBe(false);

      await transition([balances(ActivityStatus.COMPLETE), prices(ActivityStatus.RUNNING)]);
      await transition([balances(ActivityStatus.COMPLETE), prices(ActivityStatus.COMPLETE)]);
      await endBatch();

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
