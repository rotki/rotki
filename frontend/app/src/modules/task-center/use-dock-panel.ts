import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { groupTitle, isSafeToStop } from '@/modules/task-center/core/kinds';
import { isTerminalStatus, type StatusTally, tallyStatuses } from '@/modules/task-center/core/status';
import { someInSubtree, subtreeLeaves } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, type ActivityKind, ActivityStatus } from '@/modules/task-center/core/types';
import { DockState } from '@/modules/task-center/dock-state';
import { useTaskController } from '@/modules/task-center/use-task-controller';
import { useTaskDock } from '@/modules/task-center/use-task-dock';

/** A run of panel rows, under a kind heading when more than one job of that kind is listed. */
interface DockSection {
  readonly key: string;
  /** Present only when the kind repeats; a single job's own title already names it. */
  readonly title?: string;
  readonly roots: Activity[];
}

interface UseDockPanelReturn {
  /** The jobs the panel lists: in flight while working, otherwise the ones whose outcome it reports. */
  roots: ComputedRef<Activity[]>;
  sections: ComputedRef<DockSection[]>;
  /** Leaves across {@link roots}, by status, for the header's bar and counts. */
  tally: ComputedRef<StatusTally>;
  /** Leaves in {@link tally}. */
  total: ComputedRef<number>;
  title: ComputedRef<string>;
  /** Whether the header summarises; a single job's row already shows its own progress. */
  summary: ComputedRef<boolean>;
  /** Failed leaves the orchestrator can run again, while the dock reports failures. */
  retryable: ComputedRef<Activity[]>;
  /** Whether the footer's bulk retry adds anything over the rows and failure groups. */
  canRetryAll: ComputedRef<boolean>;
  retryFailed: () => void;
  /** Listed jobs a bulk stop may interrupt without leaving data half-written. See `isSafeToStop`. */
  stoppable: ComputedRef<Activity[]>;
  /** Listed jobs a bulk stop leaves running, because interrupting them could leave data half-written. */
  unstoppable: ComputedRef<Activity[]>;
}

/** How long a job must run before the panel lists it, so upkeep that finishes at once never flashes a row. */
const APPEAR_DELAY = 1000;

function isFailed(activity: Activity): boolean {
  return activity.status === ActivityStatus.FAILED;
}

/** Oldest start first; a job not yet started goes last, in id order. */
function byStart(a: Activity, b: Activity): number {
  return ((a.startedAt ?? Number.MAX_SAFE_INTEGER) - (b.startedAt ?? Number.MAX_SAFE_INTEGER)) || a.id.localeCompare(b.id);
}

/**
 * What the dock's panel lists and how its header summarises it.
 *
 * @remarks
 * Counts are leaves, the same unit the pill and each row count in, so "3 of 21 finished" in the
 * header adds up the rows beneath it.
 *
 * Nothing moves while work runs. Jobs keep the order they started in, so a new one appends below
 * rather than pushing the others down; a job that finishes stays where it is until the run ends
 * rather than leaving a gap the rows below close; and a job only appears once it has run for
 * {@link APPEAR_DELAY}, or failed, so work that is over in a moment never shows at all, nor turns up
 * in the clean report at the end (unless it is all there is). Once listed, a job stays listed. Only
 * a settled report reorders, failures first, so a mixed outcome is never below the fold.
 */
export function useDockPanel(
  jobs: MaybeRefOrGetter<PendingJob[]>,
  children: MaybeRefOrGetter<ReadonlyMap<ActivityId, Activity[]>>,
): UseDockPanelReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { dismissed, dismissedFailure, failed, finished, state } = useTaskDock();
  const { rerun } = useTaskController();

  const now = useTimestamp({ interval: 250 });

  /** Jobs the panel has listed during this stretch of work, which stay listed however briefly they ran. */
  const shown = shallowRef<ReadonlySet<ActivityId>>(new Set());

  const hasFailure = (root: Activity): boolean => someInSubtree(toValue(children), root, isFailed);

  /** Every job in flight, and every one this run finished, whatever the order they came in. */
  function working(): Activity[] {
    const all = [...toValue(jobs).map(job => job.activity), ...get(failed), ...get(finished)];
    return all.filter((root, index) => all.findIndex(other => other.id === root.id) === index);
  }

  /** Whether a job has earned its row: listed before, holding a failure, or still going past the delay. A job with no start time cannot be timed, so it lists at once. */
  function hasAppeared(root: Activity): boolean {
    if (get(shown).has(root.id) || hasFailure(root))
      return true;
    if (isTerminalStatus(root.status))
      return false;
    return root.startedAt === undefined || get(now) - root.startedAt >= APPEAR_DELAY;
  }

  function listed(): Activity[] {
    switch (get(state)) {
      case DockState.WORKING:
        return working().filter(hasAppeared);
      case DockState.FAILED:
        return get(failed);
      case DockState.DISMISSED:
        return get(dismissed);
      case DockState.DONE: {
        const seen = get(finished).filter(root => get(shown).has(root.id));
        return seen.length > 0 ? seen : get(finished);
      }
      case undefined:
        return [];
    }
  }

  const roots = computed<Activity[]>(() => {
    const ordered = [...listed()].sort(byStart);
    return get(state) === DockState.WORKING
      ? ordered
      : ordered.sort((a, b) => Number(hasFailure(b)) - Number(hasFailure(a)));
  });

  /** Remembers what was listed, and forgets it all once the dock has nothing left to show. */
  function rememberShown(list: Activity[]): void {
    if (get(state) === undefined) {
      if (get(shown).size > 0)
        set(shown, new Set());
      return;
    }
    const added = list.filter(root => !get(shown).has(root.id));
    if (added.length > 0)
      set(shown, new Set([...get(shown), ...added.map(root => root.id)]));
  }

  watch(roots, rememberShown, { immediate: true });

  /** While work runs every job is its own untitled section, so a second job of a kind appends below instead of joining the first. */
  const sections = computed<DockSection[]>(() => {
    if (get(state) === DockState.WORKING)
      return get(roots).map(root => ({ key: root.id, roots: [root] }));

    const byKind = new Map<ActivityKind, Activity[]>();
    for (const root of get(roots))
      byKind.set(root.kind, [...(byKind.get(root.kind) ?? []), root]);

    return Array.from(byKind.entries(), ([kind, list]) => ({
      key: kind,
      roots: list,
      title: list.length > 1 ? groupTitle(kind, list, t) : undefined,
    }));
  });

  const leaves = computed<Activity[]>(() => get(roots).flatMap(root => subtreeLeaves(toValue(children), root)));

  const tally = computed<StatusTally>(() => tallyStatuses(get(leaves).map(leaf => leaf.status)));

  const total = computed<number>(() => get(leaves).length);

  const reportsFailure = computed<boolean>(() => get(state) === DockState.FAILED
    || (get(state) === DockState.DISMISSED && get(dismissedFailure)));

  const title = computed<string>(() => {
    if (get(state) === DockState.WORKING)
      return t('task_dock.panel.title.working');
    return get(reportsFailure) ? t('task_dock.panel.title.problems') : t('task_dock.panel.title.finished');
  });

  const summary = computed<boolean>(() => get(roots).length > 1);

  const retryable = computed<Activity[]>(() => (get(reportsFailure)
    ? get(leaves).filter(leaf => isFailed(leaf) && leaf.rerunnable)
    : []));

  /**
   * Whether a bulk retry does more than a row already offers: it needs several retryable failures,
   * and ones that do not all sit in a single failure group, since a group of failures sharing a
   * reason under one job carries its own "retry all".
   */
  const canRetryAll = computed<boolean>(() => {
    if (get(retryable).length < 2)
      return false;
    const groups = new Set(get(roots).flatMap(root => subtreeLeaves(toValue(children), root)
      .filter(leaf => isFailed(leaf) && leaf.rerunnable)
      .map(leaf => `${root.id}:${leaf.reason ?? ''}`)));
    return groups.size > 1;
  });

  function retryFailed(): void {
    for (const leaf of get(retryable))
      rerun(leaf);
  }

  /** Safe to stop as a whole: its kind only reads or syncs, and nothing in it deletes before re-deriving. */
  const isStoppable = (root: Activity): boolean => isSafeToStop(root.kind)
    && !someInSubtree(toValue(children), root, activity => activity.resets === true);

  const running = computed<Activity[]>(() => (get(state) === DockState.WORKING
    ? get(roots).filter(root => root.cancellable)
    : []));

  const stoppable = computed<Activity[]>(() => get(running).filter(isStoppable));

  const unstoppable = computed<Activity[]>(() => get(running).filter(root => !isStoppable(root)));

  return { canRetryAll, retryable, retryFailed, roots, sections, stoppable, summary, tally, title, total, unstoppable };
}
