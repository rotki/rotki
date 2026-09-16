import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Activity, ActivityId, ActivitySteps } from '@/modules/task-center/core/types';
import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { globalKindRank } from '@/modules/task-center/core/kinds';

interface UseDockPrimaryReturn {
  /** The job the pill names, or `undefined` while everything is still queued. */
  primary: ComputedRef<PendingJob | undefined>;
  /** Whether {@link primary} is a kind the pill names; only such a job gets its title, a determinate ring and a count. */
  isPrimaryRanked: ComputedRef<boolean>;
  /**
   * The count the pill shows for {@link primary}.
   *
   * @remarks
   * A job with children counts its subtree's leaves. A single activity has no leaves to count, so it
   * uses the steps it reports itself: counted as one leaf it would read "0 of 1" beside a percentage
   * that says otherwise. `undefined` for an unranked job, or a ranked one that reports no steps.
   */
  primarySteps: ComputedRef<ActivitySteps | undefined>;
  /** Jobs in flight besides {@link primary}. */
  otherJobs: ComputedRef<number>;
}

function rankOf(job: PendingJob): number {
  return globalKindRank(job.activity.kind) ?? Number.POSITIVE_INFINITY;
}

/**
 * Picks the one job the dock's pill names while work is in flight.
 *
 * @remarks
 * The pill names one job rather than a total. Kinds report progress in different units, so a
 * combined figure would compare leaves with events, and averaging percentages makes the bar jump
 * whenever a job starts or ends. The primary job is the best-ranked job by `globalKindRank`, which
 * ranks the data a user waits to look at; with none of those running it is the first job in
 * flight, and the pill describes it generically rather than naming upkeep such as a price refresh.
 */
export function useDockPrimary(
  jobs: MaybeRefOrGetter<PendingJob[]>,
  children: MaybeRefOrGetter<ReadonlyMap<ActivityId, Activity[]>>,
): UseDockPrimaryReturn {
  const primary = computed<PendingJob | undefined>(() => toValue(jobs).reduce<PendingJob | undefined>(
    (best, job) => (best === undefined || rankOf(job) < rankOf(best) ? job : best),
    undefined,
  ));

  const isPrimaryRanked = computed<boolean>(() => {
    const job = get(primary);
    return job !== undefined && Number.isFinite(rankOf(job));
  });

  const primarySteps = computed<ActivitySteps | undefined>(() => {
    const job = get(primary);
    if (job === undefined || !get(isPrimaryRanked))
      return undefined;

    const hasChildren = (toValue(children).get(job.activity.id)?.length ?? 0) > 0;
    const count = hasChildren ? job.steps : job.activity.steps;
    return count && count.total > 0 ? count : undefined;
  });

  const otherJobs = computed<number>(() => Math.max(toValue(jobs).length - 1, 0));

  return { isPrimaryRanked, otherJobs, primary, primarySteps };
}
