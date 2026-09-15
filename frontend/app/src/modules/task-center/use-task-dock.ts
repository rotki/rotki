import type { ComputedRef, Ref } from 'vue';
import type { Activity, ActivityId, ActivitySteps } from '@/modules/task-center/core/types';
import { globalKindRank } from '@/modules/task-center/core/kinds';
import { type PendingJob, usePendingJobs } from '@/modules/task-center/use-pending-jobs';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** How long the panel stays open after the last task settles. */
const COLLAPSE_DEBOUNCE = 1000;

interface UseTaskDockReturn {
  /** Whether anything is running or queued. The dock is not rendered otherwise. */
  visible: ComputedRef<boolean>;
  /** Whether the panel is open; the pill and the panel header both toggle it. */
  modelExpanded: Ref<boolean>;
  /** Every job in flight, as the panel lists them. */
  jobs: ComputedRef<PendingJob[]>;
  /** The tree the panel's rows walk. */
  children: ComputedRef<ReadonlyMap<ActivityId, Activity[]>>;
  /** Leaves across every job in flight, for the panel header. */
  steps: ComputedRef<ActivitySteps>;
  /** Overall progress across every job, for the panel header. */
  percentage: ComputedRef<number>;
  /** The job the pill names, or `undefined` while everything is still queued. */
  primary: ComputedRef<PendingJob | undefined>;
  /** Whether {@link primary} is a long job; only a long job gets a determinate ring and a count. */
  isPrimaryLong: ComputedRef<boolean>;
  /**
   * The count the pill shows for {@link primary}.
   *
   * @remarks
   * A job with children counts its subtree's leaves. A single activity has no leaves to count, so it
   * uses the steps it reports itself: counted as one leaf it would read "0 of 1" beside a percentage
   * that says otherwise. `undefined` for a short job, or a long one that reports no steps.
   */
  primarySteps: ComputedRef<ActivitySteps | undefined>;
  /** Jobs in flight besides {@link primary}. */
  otherJobs: ComputedRef<number>;
}

function rankOf(job: PendingJob): number {
  return globalKindRank(job.activity.kind) ?? Number.POSITIVE_INFINITY;
}

/**
 * State for the corner dock: a pill naming the work in flight, and a panel listing it.
 *
 * @remarks
 * The pill names one job rather than a total. Long kinds report progress in different units, so a
 * combined figure would compare leaves with events, and averaging percentages makes the bar jump
 * whenever a job starts or ends. The primary job is the best-ranked long job; with none running it
 * is the first job in flight, shown without a count.
 */
export function useTaskDock(): UseTaskDockReturn {
  const { isActive } = useTaskCenter();
  const { children, jobs, percentage, steps } = usePendingJobs();

  const modelExpanded = shallowRef<boolean>(false);

  const primary = computed<PendingJob | undefined>(() => get(jobs).reduce<PendingJob | undefined>(
    (best, job) => (best === undefined || rankOf(job) < rankOf(best) ? job : best),
    undefined,
  ));

  const isPrimaryLong = computed<boolean>(() => {
    const job = get(primary);
    return job !== undefined && Number.isFinite(rankOf(job));
  });

  const primarySteps = computed<ActivitySteps | undefined>(() => {
    const job = get(primary);
    if (job === undefined || !get(isPrimaryLong))
      return undefined;

    const hasChildren = (get(children).get(job.activity.id)?.length ?? 0) > 0;
    const count = hasChildren ? job.steps : job.activity.steps;
    return count && count.total > 0 ? count : undefined;
  });

  const otherJobs = computed<number>(() => Math.max(get(jobs).length - 1, 0));

  function collapseWhenIdle(active: boolean): void {
    if (!active)
      set(modelExpanded, false);
  }

  watchDebounced(isActive, collapseWhenIdle, { debounce: COLLAPSE_DEBOUNCE });

  return {
    children,
    isPrimaryLong,
    jobs,
    modelExpanded,
    otherJobs,
    percentage,
    primary,
    primarySteps,
    steps,
    visible: isActive,
  };
}
