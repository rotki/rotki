import type { ComputedRef } from 'vue';
import { percentageFromSteps } from './core/status';
import { someInSubtree, subtreeSteps } from './core/tree';
import { type Activity, type ActivityId, ActivityStatus, type ActivitySteps } from './core/types';
import { useTaskCenter } from './use-task-center';

/**
 * One thing the user started, with its subtree rolled up. A "job" is a root activity: the history
 * refresh, not the eleven chain syncs and forty account queries it fans out into.
 */
export interface PendingJob {
  readonly activity: Activity;
  /** Leaf-based, so it agrees with {@link percentage}. See {@link subtreeSteps}. */
  readonly steps: ActivitySteps;
  /** 0-100, or -1 when the subtree is a single indeterminate leaf. */
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

    return get(model).roots.filter(root => someInSubtree(tree, root, isRunning)).map((activity) => {
      const steps = subtreeSteps(tree, activity);
      return { activity, percentage: percentageFromSteps(steps.current, steps.total), steps };
    });
  });

  const steps = computed<ActivitySteps>(() => get(jobs).reduce<ActivitySteps>(
    (total, job) => ({ current: total.current + job.steps.current, total: total.total + job.steps.total }),
    { current: 0, total: 0 },
  ));

  const percentage = computed<number>(() => {
    const { current, total } = get(steps);
    return percentageFromSteps(current, total);
  });

  return { children, jobs, percentage, steps };
}
