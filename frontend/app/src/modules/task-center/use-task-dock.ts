import type { ComputedRef, Ref } from 'vue';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { someInSubtree } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, ActivityStatus } from '@/modules/task-center/core/types';
import { type PendingJob, usePendingJobs } from '@/modules/task-center/use-pending-jobs';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** How long the panel stays open after the last task settles. */
const COLLAPSE_DEBOUNCE = 1000;

/** How long the pill shows the summary of a run that finished cleanly. */
const PEEK_DURATION = 6000;

export const DockState = {
  WORKING: 'working',
  /** A run just finished with nothing failed; shown for {@link PEEK_DURATION}, then the dock hides. */
  DONE: 'done',
  /** A settled job has a failure somewhere in its subtree; shown until acknowledged. */
  FAILED: 'failed',
  /** Every failure left has been acknowledged; the pill shrinks to an icon that reopens them, until the job reruns. */
  DISMISSED: 'dismissed',
} as const;

export type DockState = (typeof DockState)[keyof typeof DockState];

interface UseTaskDockReturn {
  /** What the dock is showing, or `undefined` when it is not rendered. */
  state: ComputedRef<DockState | undefined>;
  visible: ComputedRef<boolean>;
  /** Whether the panel is open; the pill and the panel header both toggle it. */
  modelExpanded: Ref<boolean>;
  /** Settled jobs with a failure anywhere in their subtree, not yet acknowledged. */
  failed: ComputedRef<Activity[]>;
  /** Settled jobs with a failure the user has acknowledged; kept reachable until the job reruns. */
  dismissed: ComputedRef<Activity[]>;
  /** Settled jobs of the last run that neither failed nor were cancelled. */
  finished: ComputedRef<Activity[]>;
  /**
   * Moves one job from {@link failed} to {@link dismissed}; a later run of it that fails again
   * reports it as failed again. The panel closes once no unacknowledged failure is left.
   */
  acknowledge: (id: ActivityId) => void;
  /** Keeps the summary on screen while the pointer or focus is on the dock. */
  holdPeek: (held: boolean) => void;
}

function isFailed(activity: Activity): boolean {
  return activity.status === ActivityStatus.FAILED;
}

/**
 * What the corner dock is showing, and whether its panel is open.
 *
 * @remarks
 * While work runs the dock is working; what it names is `useDockPrimary`'s concern and what it
 * lists is {@link usePendingJobs}'s. Once a run settles, the dock reports its outcome, and every
 * rule is bound to state rather than a timer. A clean run peeks a summary and hides. A failure stays until acknowledged, then shrinks
 * to an icon rather than vanishing, so a dismissed failure can still be reopened. Either clears on
 * its own when the job is rerun, because a rerun puts the same record back to PENDING. Only jobs
 * seen running are reported, so work that settled before the dock saw it does not resurface.
 */
export const useTaskDock = createSharedComposable((): UseTaskDockReturn => {
  const { isActive, model } = useTaskCenter();
  const { children, jobs } = usePendingJobs();

  const modelExpanded = shallowRef<boolean>(false);
  const tracked = shallowRef<ReadonlySet<ActivityId>>(new Set());
  const acknowledged = shallowRef<ReadonlySet<ActivityId>>(new Set());
  const peeking = shallowRef<boolean>(false);

  const settled = computed<Activity[]>(() => {
    const ids = get(tracked);
    return get(model).roots.filter(root => ids.has(root.id) && isTerminalStatus(root.status));
  });

  const withFailure = computed<Activity[]>(() => get(settled).filter(root => someInSubtree(get(children), root, isFailed)));

  const failed = computed<Activity[]>(() => get(withFailure).filter(root => !get(acknowledged).has(root.id)));

  const dismissed = computed<Activity[]>(() => get(withFailure).filter(root => get(acknowledged).has(root.id)));

  const finished = computed<Activity[]>(() => get(settled).filter(
    root => root.status !== ActivityStatus.CANCELLED && !someInSubtree(get(children), root, isFailed),
  ));

  const state = computed<DockState | undefined>(() => {
    if (get(isActive))
      return DockState.WORKING;
    if (get(failed).length > 0)
      return DockState.FAILED;
    if (get(peeking))
      return DockState.DONE;
    if (get(dismissed).length > 0)
      return DockState.DISMISSED;
    return undefined;
  });

  const visible = computed<boolean>(() => get(state) !== undefined);

  /** Tracks jobs as they run; a job running again drops its acknowledgement, so a new failure is reported afresh. */
  function track(list: PendingJob[]): void {
    const ids = list.map(job => job.activity.id);
    const current = get(tracked);
    const added = ids.filter(id => !current.has(id));
    if (added.length > 0)
      set(tracked, new Set([...current, ...added]));

    const seen = get(acknowledged);
    if (ids.some(id => seen.has(id)))
      set(acknowledged, new Set([...seen].filter(id => !ids.includes(id))));
  }

  /** Stops tracking the settled jobs matching `drop`, leaving live work tracked. */
  function untrack(drop: (root: Activity) => boolean): void {
    const dropped = new Set(get(settled).filter(drop).map(root => root.id));
    set(tracked, new Set([...get(tracked)].filter(id => !dropped.has(id))));
  }

  /** Forgets every settled job that holds no failure, so the next summary counts only its own run. */
  function forgetFinished(): void {
    const failedIds = new Set(get(withFailure).map(root => root.id));
    untrack(root => !failedIds.has(root.id));
  }

  function endPeek(): void {
    set(peeking, false);
    forgetFinished();
  }

  const { start: startPeek, stop: stopPeek } = useTimeoutFn(endPeek, PEEK_DURATION, { immediate: false });

  function acknowledge(id: ActivityId): void {
    set(acknowledged, new Set([...get(acknowledged), id]));
    if (get(failed).length === 0)
      set(modelExpanded, false);
  }

  function holdPeek(held: boolean): void {
    if (!get(peeking))
      return;

    if (held)
      stopPeek();
    else
      startPeek();
  }

  /**
   * Peeks the summary when a run settles cleanly.
   *
   * @remarks
   * A new run cancels a running peek and forgets the previous run's clean jobs, so its own summary
   * does not count them. A run that failed shows its failures instead of a peek, and one where
   * everything was cancelled shows nothing: the user stopped it and needs no summary of that.
   */
  function reportOutcome(active: boolean, wasActive: boolean | undefined): void {
    if (active) {
      stopPeek();
      set(peeking, false);
      forgetFinished();
      return;
    }

    if (!wasActive)
      return;

    if (get(failed).length === 0 && get(finished).length > 0) {
      set(peeking, true);
      startPeek();
    }
    else {
      forgetFinished();
    }
  }

  /** Closes the panel once work goes idle, unless it is showing failures the user has to read. */
  function collapseWhenIdle(active: boolean): void {
    if (!active && get(failed).length === 0)
      set(modelExpanded, false);
  }

  watch(jobs, track, { immediate: true });
  watch(isActive, reportOutcome);
  watchDebounced(isActive, collapseWhenIdle, { debounce: COLLAPSE_DEBOUNCE });

  return {
    acknowledge,
    dismissed,
    failed,
    finished,
    holdPeek,
    modelExpanded,
    state,
    visible,
  };
});
