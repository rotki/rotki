import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { someInSubtree, subtreeLeaves } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, ActivityStatus } from '@/modules/task-center/core/types';
import { DockState } from '@/modules/task-center/dock-state';
import { useActivityLabel } from '@/modules/task-center/use-activity-label';
import { useDockPrimary } from '@/modules/task-center/use-dock-primary';
import { useTaskDock } from '@/modules/task-center/use-task-dock';

function isFailed(activity: Activity): boolean {
  return activity.status === ActivityStatus.FAILED;
}

/**
 * The text on the dock's pill: the job in flight while working, the outcome once the run settles.
 *
 * @remarks
 * A failed job is described by its failed leaves, not blamed as a whole. One failed chain of 21
 * names that chain, several are counted against the same leaves the running pill counted, and a job
 * whose failure sits on a parent rather than a leaf falls back to its own title.
 *
 * Takes the jobs and tree the dock already holds rather than building its own copy of them.
 */
export function useTaskDockCaption(
  jobs: MaybeRefOrGetter<PendingJob[]>,
  children: MaybeRefOrGetter<ReadonlyMap<ActivityId, Activity[]>>,
): ComputedRef<string> {
  const { t } = useI18n({ useScope: 'global' });
  const { dismissed, failed, finished, state } = useTaskDock();
  const { isPrimaryRanked, primary } = useDockPrimary(jobs, children);
  const { labelOf } = useActivityLabel();

  function failedJob(root: Activity): string {
    const leaves = subtreeLeaves(toValue(children), root);
    const failedLeaves = leaves.filter(isFailed);
    const hasChildren = leaves.length > 1 || leaves[0]?.id !== root.id;

    if (!hasChildren || failedLeaves.length === 0)
      return t('task_dock.failed', { title: root.title });

    if (failedLeaves.length === 1)
      return t('task_dock.failed_leaf', { label: labelOf(failedLeaves[0], true) });

    return t('task_dock.failed_leaves', { failed: failedLeaves.length, title: root.title, total: leaves.length });
  }

  function failures(roots: Activity[]): string {
    return roots.length === 1
      ? failedJob(roots[0])
      : t('task_dock.failed_count', { count: roots.length }, roots.length);
  }

  function successes(roots: Activity[]): string {
    return roots.length === 1
      ? t('task_dock.done', { title: roots[0].title })
      : t('task_dock.done_count', { count: roots.length }, roots.length);
  }

  /** Dismissed jobs are described by their failures when they hold any, the way the icon they shrink to is. */
  function dismissedCaption(): string {
    const withFailure = get(dismissed).filter(root => someInSubtree(toValue(children), root, isFailed));
    return withFailure.length > 0 ? failures(withFailure) : successes(get(dismissed));
  }

  return computed<string>(() => {
    switch (get(state)) {
      case DockState.FAILED:
        return failures(get(failed));
      case DockState.DISMISSED:
        return dismissedCaption();
      case DockState.DONE:
        return successes(get(finished));
      case DockState.WORKING:
      case undefined: {
        const job = get(primary);
        if (!job)
          return t('task_dock.queued');
        return get(isPrimaryRanked) ? job.activity.title : t('task_dock.updating');
      }
    }
  });
}
