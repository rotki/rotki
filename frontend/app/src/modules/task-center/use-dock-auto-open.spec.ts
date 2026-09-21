import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { type Activity, ActivityKind, ActivitySourceType, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';
import { DockState } from './dock-state';
import { useDockAutoOpen } from './use-dock-auto-open';

const showSummary = ref<boolean>(true);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<boolean> => showSummary,
}));

function job(name: string, userStarted = false): PendingJob {
  const activity: Activity = {
    cancellable: true,
    id: makeActivityId(ActivityKind.HISTORY_SYNC, name),
    kind: ActivityKind.HISTORY_SYNC,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    title: name,
    userStarted,
  };
  return { activity, percentage: -1, steps: { current: 0, total: 1 } };
}

const isActive = ref<boolean>(false);
const working = ref<boolean>(false);
const jobs = ref<PendingJob[]>([]);
const failed = ref<Activity[]>([]);
const finished = ref<Activity[]>([]);
const interacting = ref<boolean>(false);
const modelExpanded = ref<boolean>(false);

let scope: ReturnType<typeof effectScope> | undefined;
let batch: Activity[] = [];

function autoOpen(failedBeforeMount: Activity[] = []): void {
  scope?.stop();
  scope = effectScope();
  scope.run(() => useDockAutoOpen({
    failed,
    failedBeforeMount: failedBeforeMount.map(activity => activity.id),
    finished,
    interacting,
    isActive,
    jobs,
    modelExpanded,
    working,
  }));
}

/** Starts a batch; like the dock, it replaces the last batch's clean runs and keeps its failures. */
async function start(...list: PendingJob[]): Promise<void> {
  batch = list.map(pending => pending.activity);
  set(jobs, list);
  set(finished, []);
  set(isActive, true);
  set(working, true);
  await nextTick();
}

/** The work goes idle for a moment, inside the batch's grace period. */
async function pause(): Promise<void> {
  set(jobs, []);
  set(working, false);
  await nextTick();
}

async function settle(outcome: typeof DockState.DONE | typeof DockState.FAILED): Promise<void> {
  set(jobs, []);
  set(isActive, false);
  set(working, false);
  if (outcome === DockState.FAILED)
    set(failed, [...get(failed), ...batch]);
  else
    set(finished, batch);
  await nextTick();
}

describe('useDockAutoOpen', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    set(showSummary, true);
    set(isActive, false);
    set(working, false);
    batch = [];
    set(jobs, []);
    set(failed, []);
    set(finished, []);
    set(interacting, false);
    set(modelExpanded, false);
    autoOpen();
  });

  afterEach(() => {
    scope?.stop();
    vi.useRealTimers();
  });

  describe('while work runs', () => {
    it('should open the panel for a job the user started', async () => {
      await start(job('refresh', true));

      expect(get(modelExpanded)).toBe(true);
    });

    it('should leave the panel shut for work that started on its own', async () => {
      await start(job('login-load'));

      expect(get(modelExpanded)).toBe(false);
    });

    it('should not reopen for another job the user starts after they collapsed it during the batch', async () => {
      await start(job('refresh', true));
      set(modelExpanded, false);
      await nextTick();

      set(jobs, [job('refresh', true), job('report', true)]);
      await nextTick();

      expect(get(modelExpanded)).toBe(false);
    });

    it('should open for a job the user starts once the collapsed work went idle, though the batch has not ended', async () => {
      await start(job('refresh', true));
      set(modelExpanded, false);
      await nextTick();
      await pause();

      await start(job('report', true));

      expect(get(modelExpanded)).toBe(true);
    });

    it('should still skip the summary of a batch collapsed before a pause in it', async () => {
      await start(job('refresh', true));
      set(modelExpanded, false);
      await nextTick();
      await pause();
      await start(job('prices'));

      await settle(DockState.DONE);

      expect(get(modelExpanded)).toBe(false);
    });

    it('should open again for the next batch once the collapsed one settles', async () => {
      await start(job('refresh', true));
      set(modelExpanded, false);
      await nextTick();
      await settle(DockState.DONE);

      await start(job('report', true));

      expect(get(modelExpanded)).toBe(true);
    });
  });

  describe('when a batch settles', () => {
    it('should show a clean run\'s summary, then fold it back into the pill', async () => {
      await start(job('login-load'));
      await settle(DockState.DONE);

      expect(get(modelExpanded)).toBe(true);

      await vi.advanceTimersByTimeAsync(6000);

      expect(get(modelExpanded)).toBe(false);
    });

    it('should hold the summary open while the dock is hovered, and give it the full time again once left', async () => {
      await start(job('login-load'));
      await settle(DockState.DONE);

      set(interacting, true);
      await nextTick();
      await vi.advanceTimersByTimeAsync(10_000);
      expect(get(modelExpanded)).toBe(true);

      set(interacting, false);
      await nextTick();
      await vi.advanceTimersByTimeAsync(5000);
      expect(get(modelExpanded)).toBe(true);

      await vi.advanceTimersByTimeAsync(1000);
      expect(get(modelExpanded)).toBe(false);
    });

    it('should keep a failed run open, since failures stay until dismissed', async () => {
      await start(job('login-load'));
      await settle(DockState.FAILED);

      await vi.advanceTimersByTimeAsync(60_000);

      expect(get(modelExpanded)).toBe(true);
    });

    it('should show no summary when the setting is off', async () => {
      set(showSummary, false);
      await start(job('login-load'));
      await settle(DockState.FAILED);

      expect(get(modelExpanded)).toBe(false);
    });

    it('should skip the summary of a batch the user collapsed the panel during', async () => {
      await start(job('refresh', true));
      set(modelExpanded, false);
      await nextTick();

      await settle(DockState.DONE);

      expect(get(modelExpanded)).toBe(false);
    });

    it('should leave a panel the user already has open as it is', async () => {
      await start(job('refresh', true));
      await settle(DockState.DONE);

      await vi.advanceTimersByTimeAsync(60_000);

      expect(get(modelExpanded)).toBe(true);
    });

    it('should end a summary when the next batch starts on its own', async () => {
      await start(job('login-load'));
      await settle(DockState.DONE);

      await start(job('periodic'));

      expect(get(modelExpanded)).toBe(false);
    });

    it('should still summarize a batch that ended the previous summary', async () => {
      await start(job('login-load'));
      await settle(DockState.DONE);
      await start(job('periodic'));

      await settle(DockState.FAILED);

      expect(get(modelExpanded)).toBe(true);
    });

    it('should not hold the panel open on a failure left from an earlier batch', async () => {
      await start(job('login-load'));
      await settle(DockState.FAILED);
      set(modelExpanded, false);
      await nextTick();

      await start(job('periodic'));
      await settle(DockState.DONE);
      await vi.advanceTimersByTimeAsync(6000);

      expect(get(modelExpanded)).toBe(false);
    });

    it('should report a failure from before the dock mounted with the batch running at mount', async () => {
      const early = job('migration').activity;
      set(isActive, true);
      autoOpen([early]);
      set(failed, [early]);

      await settle(DockState.DONE);
      await vi.advanceTimersByTimeAsync(60_000);

      expect(get(modelExpanded)).toBe(true);
    });
  });
});
