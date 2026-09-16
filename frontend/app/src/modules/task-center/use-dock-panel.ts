import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { groupTitle, isSafeToStop } from '@/modules/task-center/core/kinds';
import { type StatusTally, tallyStatuses } from '@/modules/task-center/core/status';
import { someInSubtree, subtreeLeaves } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, type ActivityKind, ActivityStatus } from '@/modules/task-center/core/types';
import { useTaskController } from '@/modules/task-center/use-task-controller';
import { DockState, useTaskDock } from '@/modules/task-center/use-task-dock';

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
  retryFailed: () => void;
  /** Listed jobs a bulk stop may interrupt without leaving data half-written. See `isSafeToStop`. */
  stoppable: ComputedRef<Activity[]>;
  /** Listed jobs a bulk stop leaves running, because interrupting them could leave data half-written. */
  unstoppable: ComputedRef<Activity[]>;
}

function isFailed(activity: Activity): boolean {
  return activity.status === ActivityStatus.FAILED;
}

/**
 * What the dock's panel lists and how its header summarises it.
 *
 * @remarks
 * Counts are leaves, the same unit the pill and each row count in, so "3 of 21 finished" in the
 * header adds up the rows beneath it. Jobs holding a failure sort first, so a mixed outcome is
 * never below the fold.
 */
export function useDockPanel(
  jobs: MaybeRefOrGetter<PendingJob[]>,
  children: MaybeRefOrGetter<ReadonlyMap<ActivityId, Activity[]>>,
): UseDockPanelReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { dismissed, failed, finished, state } = useTaskDock();
  const { rerun } = useTaskController();

  const hasFailure = (root: Activity): boolean => someInSubtree(toValue(children), root, isFailed);

  function listed(): Activity[] {
    switch (get(state)) {
      case DockState.WORKING:
        return toValue(jobs).map(job => job.activity);
      case DockState.FAILED:
        return get(failed);
      case DockState.DISMISSED:
        return get(dismissed);
      case DockState.DONE:
        return get(finished);
      case undefined:
        return [];
    }
  }

  const roots = computed<Activity[]>(() => [...listed()].sort((a, b) => Number(hasFailure(b)) - Number(hasFailure(a))));

  const sections = computed<DockSection[]>(() => {
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

  const reportsFailure = computed<boolean>(() => get(state) === DockState.FAILED || get(state) === DockState.DISMISSED);

  const title = computed<string>(() => {
    if (get(state) === DockState.WORKING)
      return t('task_dock.panel.title.working');
    return get(reportsFailure) ? t('task_dock.panel.title.problems') : t('task_dock.panel.title.finished');
  });

  const summary = computed<boolean>(() => get(roots).length > 1);

  const retryable = computed<Activity[]>(() => (get(reportsFailure)
    ? get(leaves).filter(leaf => isFailed(leaf) && leaf.rerunnable)
    : []));

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

  return { retryable, retryFailed, roots, sections, stoppable, summary, tally, title, total, unstoppable };
}
