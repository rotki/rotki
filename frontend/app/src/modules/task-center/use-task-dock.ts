import type { ComputedRef, Ref } from 'vue';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { someInSubtree } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, ActivityStatus } from '@/modules/task-center/core/types';
import { type PendingJob, usePendingJobs } from '@/modules/task-center/use-pending-jobs';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** How long the panel stays open after the last task settles. */
const COLLAPSE_DEBOUNCE = 1000;

/** How long the dismissed icon waits, collapsed and untouched, before the dock goes away. */
const DISMISSED_HIDE_DELAY = 10_000;

export const DockState = {
  WORKING: 'working',
  /** The last run finished with nothing failed; shown until dismissed or a new run starts. */
  DONE: 'done',
  /** A settled job has a failure somewhere in its subtree; shown until dismissed. */
  FAILED: 'failed',
  /**
   * Everything reported has been dismissed; the pill shrinks to an icon that reopens it, and goes
   * away after {@link DISMISSED_HIDE_DELAY} collapsed with no interaction.
   */
  DISMISSED: 'dismissed',
} as const;

export type DockState = (typeof DockState)[keyof typeof DockState];

interface UseTaskDockReturn {
  /** What the dock is showing, or `undefined` when it is not rendered. */
  state: ComputedRef<DockState | undefined>;
  visible: ComputedRef<boolean>;
  /** Whether the panel is open; the pill and the panel header both toggle it. */
  modelExpanded: Ref<boolean>;
  /** Settled jobs with a failure anywhere in their subtree, not yet dismissed. */
  failed: ComputedRef<Activity[]>;
  /** Settled jobs that neither failed nor were cancelled, not yet dismissed. */
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
  /** Marks the pointer or focus as on the dock, which holds off it going away; `false` when it leaves. */
  holdInteraction: (held: boolean) => void;
}

function isFailed(activity: Activity): boolean {
  return activity.status === ActivityStatus.FAILED;
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
 * - A clean run stays until dismissed, or until a new run starts, which replaces it.
 * - A dismissed job shrinks to an icon rather than vanishing, so it can still be reopened. The dock
 * only goes away once everything is dismissed, the panel is collapsed, and nobody has touched the
 * dock for {@link DISMISSED_HIDE_DELAY}; hovering or focusing it starts that wait over.
 * - A run the user cancelled reports nothing, since they stopped it themselves.
 *
 * Only jobs seen running are reported, so work that settled before the dock saw it does not resurface.
 */
export const useTaskDock = createSharedComposable((): UseTaskDockReturn => {
  const { isActive, model } = useTaskCenter();
  const { children, jobs } = usePendingJobs();

  const modelExpanded = shallowRef<boolean>(false);
  const tracked = shallowRef<ReadonlySet<ActivityId>>(new Set());
  const acknowledged = shallowRef<ReadonlySet<ActivityId>>(new Set());

  const hasFailure = (root: Activity): boolean => someInSubtree(get(children), root, isFailed);

  const settled = computed<Activity[]>(() => {
    const ids = get(tracked);
    return get(model).roots.filter(root => ids.has(root.id) && isTerminalStatus(root.status));
  });

  /** Settled jobs worth reporting: a failure anywhere, or a run that was not cancelled. */
  const reported = computed<Activity[]>(() => get(settled).filter(root => hasFailure(root) || root.status !== ActivityStatus.CANCELLED));

  const failed = computed<Activity[]>(() => get(reported).filter(root => hasFailure(root) && !get(acknowledged).has(root.id)));

  const finished = computed<Activity[]>(() => get(reported).filter(root => !hasFailure(root) && !get(acknowledged).has(root.id)));

  const dismissed = computed<Activity[]>(() => get(reported).filter(root => get(acknowledged).has(root.id)));

  const dismissedFailure = computed<boolean>(() => get(dismissed).some(hasFailure));

  const state = computed<DockState | undefined>(() => {
    if (get(isActive))
      return DockState.WORKING;
    if (get(failed).length > 0)
      return DockState.FAILED;
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
   * Forgets the previous run's settled jobs that hold no failure when a new run starts, so its
   * outcome replaces theirs. Failures stay: they are only cleared by dismissing or rerunning them.
   */
  function replacePreviousRun(active: boolean, wasActive: boolean | undefined): void {
    if (!active || wasActive)
      return;

    const kept = new Set(get(settled).filter(hasFailure).map(root => root.id));
    const replaced = new Set(get(settled).filter(root => !kept.has(root.id)).map(root => root.id));
    set(tracked, new Set([...get(tracked)].filter(id => !replaced.has(id))));
    set(acknowledged, new Set([...get(acknowledged)].filter(id => !replaced.has(id))));
  }

  function acknowledge(id: ActivityId): void {
    set(acknowledged, new Set([...get(acknowledged), id]));
    if (get(failed).length === 0 && get(finished).length === 0)
      set(modelExpanded, false);
  }

  /**
   * Closes the panel once work goes idle with nothing left to show, as after a run the user
   * cancelled, so it does not spring open with the next run. A panel showing an outcome, dismissed
   * ones included, stays open: the user may be reading it, and it is theirs to close.
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

  watch(jobs, track, { immediate: true });
  watch(isActive, replacePreviousRun);
  watchDebounced(isActive, collapseWhenIdle, { debounce: COLLAPSE_DEBOUNCE });
  watch([state, modelExpanded, interacting], scheduleHide, { immediate: true });

  return {
    acknowledge,
    holdInteraction,
    dismissed,
    dismissedFailure,
    failed,
    finished,
    modelExpanded,
    state,
    visible,
  };
});
