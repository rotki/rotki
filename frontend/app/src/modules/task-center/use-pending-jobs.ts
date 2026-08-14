import type { ComputedRef } from 'vue';
import { INDETERMINATE } from './core/status';
import { someInSubtree, subtreeProgress, subtreeSteps } from './core/tree';
import { type Activity, type ActivityId, ActivityStatus, type ActivitySteps } from './core/types';
import { useTaskCenter } from './use-task-center';

/**
 * One thing the user started, with its subtree rolled up. A "job" is a root activity: the history
 * refresh, not the eleven chain syncs and forty account queries it fans out into.
 */
interface PendingJob {
  readonly activity: Activity;
  /** The integer leaf tally the row's text shows. See {@link subtreeSteps}. */
  readonly steps: ActivitySteps;
  /** 0-100, or -1 when no leaf in the subtree can be quantified. See {@link subtreeProgress}. */
  readonly percentage: number;
}

interface UsePendingJobsReturn {
  jobs: ComputedRef<PendingJob[]>;
  /** Leaves across every live job — the panel's denominator. */
  steps: ComputedRef<ActivitySteps>;
  percentage: ComputedRef<number>;
  /** The whole tree, so the recursive row component walks it without re-deriving anything. */
  children: ComputedRef<ReadonlyMap<ActivityId, Activity[]>>;
}

function isRunning(activity: Activity): boolean {
  return activity.status === ActivityStatus.RUNNING;
}

/**
 * The panel's view of the orchestrator: live work as a list of jobs rather than a flat list of
 * every activity in flight.
 *
 * A job is listed while **anything in its subtree is RUNNING**. That keeps the rule the flat panel
 * had — a fully queued tree is not shown, since producers declare every account of every chain up
 * front and listing those would bury the running work under dozens of rows that have not begun —
 * while fixing what it got wrong: cancelling the last running leaf no longer leaves a card headed
 * "0 pending tasks" spinning above its queued siblings, because the job goes with them.
 */
export function usePendingJobs(): UsePendingJobsReturn {
  const { model } = useTaskCenter();

  const children = computed<ReadonlyMap<ActivityId, Activity[]>>(() => get(model).children);

  const jobs = computed<PendingJob[]>(() => {
    const tree = get(children);

    return get(model).roots.filter(root => someInSubtree(tree, root, isRunning)).map(activity => ({
      activity,
      percentage: subtreeProgress(tree, activity),
      steps: subtreeSteps(tree, activity),
    }));
  });

  const steps = computed<ActivitySteps>(() => get(jobs).reduce<ActivitySteps>(
    (total, job) => ({ current: total.current + job.steps.current, total: total.total + job.steps.total }),
    { current: 0, total: 0 },
  ));

  // Weighted by leaves, so a one-leaf job does not count for as much as an eleven-chain refresh.
  // A job nobody can quantify keeps its leaves in the denominator and contributes nothing, which is
  // the same rule `subtreeProgress` applies inside one subtree — unknown work reads as unfinished.
  const percentage = computed<number>(() => {
    const list = get(jobs);
    const total = get(steps).total;
    const quantifiable = list.filter(job => job.percentage >= 0);

    if (total === 0 || quantifiable.length === 0)
      return INDETERMINATE;

    const done = quantifiable.reduce((sum, job) => sum + (job.percentage / 100) * job.steps.total, 0);
    return Math.round((done / total) * 100);
  });

  return { children, jobs, percentage, steps };
}
