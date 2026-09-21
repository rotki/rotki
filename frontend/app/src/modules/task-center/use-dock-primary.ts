import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { globalKindRank } from '@/modules/task-center/core/kinds';
import { type Activity, type ActivityId, ActivityStatus, type ActivitySteps } from '@/modules/task-center/core/types';

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

function isNamed(job: PendingJob): boolean {
  return Boolean(job.activity.userStarted) || Number.isFinite(rankOf(job));
}

/** Whether the job has started; a job listed while it is still held back has not. */
function hasStarted(job: PendingJob): boolean {
  return job.activity.status !== ActivityStatus.PENDING;
}

/** Whether `job` should be named ahead of `best`: work that has started first, then a job the user started, then the better kind. */
function outranks(job: PendingJob, best: PendingJob): boolean {
  if (hasStarted(job) !== hasStarted(best))
    return hasStarted(job);

  const started = Boolean(job.activity.userStarted);
  if (started !== Boolean(best.activity.userStarted))
    return started;
  return rankOf(job) < rankOf(best);
}

/**
 * Picks the one job the dock's pill names while work is in flight.
 *
 * @remarks
 * The pill names one job rather than a total. Kinds report progress in different units, so a
 * combined figure would compare leaves with events, and averaging percentages makes the bar jump
 * whenever a job starts or ends. Work that has started comes before a job listed only because it is
 * held back, which the pill would otherwise name while nothing in it moves. Then a job the user
 * started comes first, whatever its kind, since it is the one they are waiting on. After that the primary job is the best-ranked job by
 * `globalKindRank`, which ranks the data a user waits to look at; with none of those running it is
 * the first job in flight, and the pill describes it generically rather than naming upkeep such as
 * a price refresh the user did not ask for.
 */
export function useDockPrimary(
  jobs: MaybeRefOrGetter<PendingJob[]>,
  children: MaybeRefOrGetter<ReadonlyMap<ActivityId, Activity[]>>,
): UseDockPrimaryReturn {
  const primary = computed<PendingJob | undefined>(() => toValue(jobs).reduce<PendingJob | undefined>(
    (best, job) => (best === undefined || outranks(job, best) ? job : best),
    undefined,
  ));

  const isPrimaryRanked = computed<boolean>(() => {
    const job = get(primary);
    return job !== undefined && isNamed(job);
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
