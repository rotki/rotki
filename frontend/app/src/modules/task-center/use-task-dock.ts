import type { ComputedRef, Ref } from 'vue';
import { backgroundTaskRun } from '@/modules/task-center/background/background-task.activity';
import { isTerminalStatus, needsAttention } from '@/modules/task-center/core/status';
import { someInSubtree } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, ActivityKind, ActivityStatus } from '@/modules/task-center/core/types';
import { DISMISSED_HIDE_DELAY, DockState } from '@/modules/task-center/dock-state';
import { useDockAutoOpen } from '@/modules/task-center/use-dock-auto-open';
import { type PendingJob, usePendingJobs } from '@/modules/task-center/use-pending-jobs';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/**
 * How long work has to stay idle before its batch counts as over. Work often goes idle for a moment
 * between stages, as the login load does between balances and prices; work that resumes sooner
 * belongs to the same batch.
 */
const BATCH_GRACE = 1000;

interface UseTaskDockReturn {
  /** What the dock is showing, or `undefined` when it is not rendered. */
  state: ComputedRef<DockState | undefined>;
  visible: ComputedRef<boolean>;
  /** Whether the panel is open; the pill and the panel header both toggle it. */
  modelExpanded: Ref<boolean>;
  /** Settled jobs with a failure anywhere in their subtree, not yet dismissed. */
  failed: ComputedRef<Activity[]>;
  /** Settled jobs held for the user by a skip that asked for attention, with no failure, not yet dismissed. */
  flagged: ComputedRef<Activity[]>;
  /** Settled jobs with nothing held for the user, cancelled ones included, not yet dismissed. */
  finished: ComputedRef<Activity[]>;
  /** Settled jobs the user has dismissed, failed or not; still reachable from the icon. */
  dismissed: ComputedRef<Activity[]>;
  /** Whether any dismissed job holds a failure, which decides the icon it shrinks to. */
  dismissedFailure: ComputedRef<boolean>;
  /**
   * Dismisses one reported job. A later run of it reports afresh. The panel closes once nothing is
   * left to read.
   */
  acknowledge: (id: ActivityId) => void;
  /**
   * Dismisses every reported job that finished with nothing held for the user, as {@link acknowledge}
   * does one, including work too brief for the panel to list, which would otherwise take the rows' place.
   */
  acknowledgeFinished: () => void;
  /** Marks the pointer or focus as on the dock, which holds off it going away; `false` when it leaves. */
  holdInteraction: (held: boolean) => void;
}

function isFailed(activity: Activity): boolean {
  return activity.status === ActivityStatus.FAILED;
}

function isBackgroundTask(activity: Activity): boolean {
  return activity.kind === ActivityKind.BACKGROUND_TASK;
}

/**
 * What the corner dock is showing, and whether its panel is open.
 *
 * @remarks
 * While work runs the dock is working; what it names is `useDockPrimary`'s concern and what it
 * lists is {@link usePendingJobs}'s. Once a run settles, the dock reports its outcome and keeps
 * reporting it: the dock is the one place a user sees what happened, so nothing leaves on a timer.
 *
 * - A failure stays until dismissed, and clears on its own when the job is rerun, because a rerun
 * puts the same record back to PENDING.
 * - A clean run stays until dismissed, or until a new batch starts, which replaces it. Work that
 * resumes within {@link BATCH_GRACE} is the same batch, so it adds to the outcome instead.
 * - A dismissed job shrinks to an icon rather than vanishing, so it can still be reopened. The dock
 * only goes away once everything is dismissed, the panel is collapsed, and nobody has touched the
 * dock for {@link DISMISSED_HIDE_DELAY}; hovering or focusing it starts that wait over.
 * - A run the user stopped is reported like a clean one, as cancelled, so it stays where it was
 * until dismissed rather than vanishing from under the user.
 *
 * Only jobs seen running are reported, so work that settled before the dock saw it does not resurface.
 * The exception is a failure: one that settled before the dock mounted, as work started during login
 * can, is reported anyway, since nowhere else shows it. The ledger is reset on logout, so what is
 * there at mount belongs to this session.
 *
 * A backend background task is shown while it runs, but is not part of a batch: it neither holds a
 * batch open nor opens the panel, and a clean finish is not reported, since the user did not ask
 * for it. Its failure is reported like any other, even one that arrives already failed, as a failure
 * the backend held while no client was connected does. A later failure of the same row replaces
 * the earlier one, so a task that fails on every run shows one failed row.
 */
export const useTaskDock = createSharedComposable((): UseTaskDockReturn => {
  const { isActive, model } = useTaskCenter();
  const { children, jobs } = usePendingJobs();

  const hasFailure = (root: Activity): boolean => someInSubtree(get(children), root, isFailed);

  /** A failure, or a skip that asked for attention, anywhere beneath the job: either holds it for the user. */
  const isHeld = (root: Activity): boolean => someInSubtree(get(children), root, needsAttention);

  /** Jobs that failed before the dock mounted; see the remarks on {@link useTaskDock}. */
  const failedBeforeMount = get(model).roots.filter(root => isTerminalStatus(root.status) && hasFailure(root)).map(root => root.id);

  /** Whether work other than background tasks is running or queued; only that work makes a batch. */
  const foregroundActive = computed<boolean>(() => {
    const { active, pending } = get(model);
    return [...active, ...pending].some(activity => !isBackgroundTask(activity));
  });

  const modelExpanded = shallowRef<boolean>(false);
  /** Whether a batch is under way: set as soon as work runs, cleared once it stays idle for {@link BATCH_GRACE}. */
  const batchActive = shallowRef<boolean>(get(foregroundActive));
  const tracked = shallowRef<ReadonlySet<ActivityId>>(new Set(failedBeforeMount));
  const acknowledged = shallowRef<ReadonlySet<ActivityId>>(new Set());

  const settled = computed<Activity[]>(() => {
    const ids = get(tracked);
    return get(model).roots.filter(root => ids.has(root.id) && isTerminalStatus(root.status));
  });

  const failed = computed<Activity[]>(() => get(settled).filter(root => hasFailure(root) && !get(acknowledged).has(root.id)));

  const flagged = computed<Activity[]>(() => get(settled).filter(root => isHeld(root) && !hasFailure(root) && !get(acknowledged).has(root.id)));

  const finished = computed<Activity[]>(() => get(settled).filter(root => !isHeld(root) && !isBackgroundTask(root) && !get(acknowledged).has(root.id)));

  const held = computed<Activity[]>(() => [...get(failed), ...get(flagged)]);

  /** The held jobs that may open the panel: a background task's failure only marks the pill. */
  const heldForeground = computed<Activity[]>(() => get(held).filter(root => !isBackgroundTask(root)));

  const dismissed = computed<Activity[]>(() => get(settled).filter(root => get(acknowledged).has(root.id)));

  const dismissedFailure = computed<boolean>(() => get(dismissed).some(hasFailure));

  const state = computed<DockState | undefined>(() => {
    if (get(isActive))
      return DockState.WORKING;
    if (get(failed).length > 0)
      return DockState.FAILED;
    if (get(flagged).length > 0)
      return DockState.ATTENTION;
    if (get(finished).length > 0)
      return DockState.DONE;
    if (get(dismissed).length > 0)
      return DockState.DISMISSED;
    return undefined;
  });

  const visible = computed<boolean>(() => get(state) !== undefined);

  /** Tracks jobs as they run; a job running again drops its acknowledgement, so its new outcome is reported afresh. */
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

  /**
   * Forgets the previous batch's settled jobs that are not held for the user when a new batch
   * starts, so its outcome replaces theirs. Held jobs stay: they are only cleared by dismissing or
   * rerunning them.
   */
  function replacePreviousRun(active: boolean, wasActive: boolean | undefined): void {
    if (!active || wasActive)
      return;

    const kept = new Set(get(settled).filter(isHeld).map(root => root.id));
    const replaced = new Set(get(settled).filter(root => !kept.has(root.id)).map(root => root.id));
    set(tracked, new Set([...get(tracked)].filter(id => !replaced.has(id))));
    set(acknowledged, new Set([...get(acknowledged)].filter(id => !replaced.has(id))));
  }

  /** The background failures already tracked, so a dismissed one is not tracked again. */
  const trackedBackgroundFailures = new Set<ActivityId>();

  /**
   * Tracks a background task's failure even when it was never seen running: a failure the backend
   * held while no client was connected arrives already settled. An entry is forgotten once its
   * activity is gone, as on logout.
   */
  function trackBackgroundFailures(roots: Activity[]): void {
    const present = new Set<ActivityId>(roots.map(root => root.id));
    for (const id of trackedBackgroundFailures) {
      if (!present.has(id))
        trackedBackgroundFailures.delete(id);
    }

    const fresh = roots.filter(root => isBackgroundTask(root) && isFailed(root) && !trackedBackgroundFailures.has(root.id)).map(root => root.id);
    if (fresh.length === 0)
      return;
    for (const id of fresh)
      trackedBackgroundFailures.add(id);
    const superseded = supersededFailures(roots);
    set(tracked, new Set([...get(tracked), ...fresh].filter(id => !superseded.has(id))));
    set(acknowledged, new Set([...get(acknowledged)].filter(id => !superseded.has(id))));
  }

  /**
   * The background failures a later failure of the same row replaces. A task that keeps failing,
   * as an indexer that stays down does on every scheduler run, then shows one failed row with its
   * latest error rather than one per run.
   */
  function supersededFailures(roots: Activity[]): Set<ActivityId> {
    const latest = new Map<string, { id: ActivityId; run: number }>();
    const superseded = new Set<ActivityId>();
    for (const root of roots) {
      if (!isBackgroundTask(root) || !isFailed(root))
        continue;
      const { row, run } = backgroundTaskRun(root);
      const previous = latest.get(row);
      if (previous === undefined || previous.run < run) {
        if (previous)
          superseded.add(previous.id);
        latest.set(row, { id: root.id, run });
      }
      else {
        superseded.add(root.id);
      }
    }
    return superseded;
  }

  function acknowledgeAll(ids: ActivityId[]): void {
    set(acknowledged, new Set([...get(acknowledged), ...ids]));
    if (get(held).length === 0 && get(finished).length === 0)
      set(modelExpanded, false);
  }

  function acknowledge(id: ActivityId): void {
    acknowledgeAll([id]);
  }

  function acknowledgeFinished(): void {
    acknowledgeAll(get(finished).map(root => root.id));
  }

  /**
   * Closes the panel once work goes idle with nothing left to show, so it does not spring open with
   * the next run. A panel showing an outcome, dismissed ones included, stays open: the user may be
   * reading it, and it is theirs to close.
   */
  function collapseWhenIdle(active: boolean): void {
    if (!active && get(state) === undefined)
      set(modelExpanded, false);
  }

  const interacting = shallowRef<boolean>(false);

  /** Forgets every dismissed job, which takes the dock away until something new is reported. */
  function forgetDismissed(): void {
    const gone = new Set(get(dismissed).map(root => root.id));
    set(tracked, new Set([...get(tracked)].filter(id => !gone.has(id))));
    set(acknowledged, new Set([...get(acknowledged)].filter(id => !gone.has(id))));
  }

  const { start: startHide, stop: stopHide } = useTimeoutFn(forgetDismissed, DISMISSED_HIDE_DELAY, { immediate: false });

  function holdInteraction(held: boolean): void {
    set(interacting, held);
  }

  /** Counts down only while the dock is just the dismissed icon, collapsed and untouched; anything else starts the wait over. */
  function scheduleHide([current, expanded, touched]: [DockState | undefined, boolean, boolean]): void {
    stopHide();
    if (current === DockState.DISMISSED && !expanded && !touched)
      startHide();
  }

  const { start: startBatchEnd, stop: stopBatchEnd } = useTimeoutFn(() => set(batchActive, false), BATCH_GRACE, { immediate: false });

  function followActivity(active: boolean): void {
    if (active) {
      stopBatchEnd();
      set(batchActive, true);
    }
    else {
      startBatchEnd();
    }
  }

  watch(jobs, track, { immediate: true });
  watch(() => get(model).roots, trackBackgroundFailures, { immediate: true });
  watch(foregroundActive, followActivity);
  watch(batchActive, replacePreviousRun);
  watch(batchActive, collapseWhenIdle);
  watch([state, modelExpanded, interacting], scheduleHide, { immediate: true });
  useDockAutoOpen({ failedBeforeMount, finished, held: heldForeground, interacting, isActive: batchActive, jobs, modelExpanded, working: foregroundActive });

  return {
    acknowledge,
    acknowledgeFinished,
    holdInteraction,
    dismissed,
    dismissedFailure,
    failed,
    finished,
    flagged,
    modelExpanded,
    state,
    visible,
  };
});
