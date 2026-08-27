import { type ActivityStatus, ActivityStatus as Status, type WorkStatus } from './types';

/** Sentinel percentage for work whose completion cannot be quantified. */
export const INDETERMINATE = -1;

/**
 * Whether a guarded fetch should skip this run.
 *
 * @remarks
 * The standing gate for "load once, then only on request": already loaded and nobody asked, or a
 * run is in flight. A user-initiated refresh passes the freshness half but still waits behind an
 * active run, so a double click cannot start two.
 *
 * @param status - the kind's projected status, from `statusOf`
 * @param userInitiated - whether the user asked for this refresh, rather than a lifecycle hook
 * @returns whether to return early instead of fetching
 */
export function shouldSkipFetch(status: WorkStatus, userInitiated: boolean): boolean {
  return (status.everCompleted && !userInitiated) || status.active;
}

/**
 * Precedence for deduplicating activities that share an id (the same work surfaced by two
 * sources — e.g. a floor task and its native producer during migration). Lower wins: a live
 * RUNNING/PENDING activity is kept over a terminal one.
 */
const STATUS_RANK: Record<ActivityStatus, number> = {
  [Status.RUNNING]: 0,
  [Status.PENDING]: 1,
  [Status.FAILED]: 2,
  [Status.CANCELLED]: 3,
  [Status.COMPLETE]: 4,
  // Least informative: if one source ran the work and another skipped it, the run wins.
  [Status.SKIPPED]: 5,
};

export function statusRank(status: ActivityStatus): number {
  return STATUS_RANK[status];
}

/** True for statuses that represent finished work (no further progress expected). */
export function isTerminalStatus(status: ActivityStatus): boolean {
  return status === Status.COMPLETE || status === Status.CANCELLED || status === Status.FAILED
    || status === Status.SKIPPED;
}

/** Naive step percentage, rounded; {@link INDETERMINATE} when the total is unknown. */
export function percentageFromSteps(processed: number, total: number): number {
  return total > 0 ? Math.round((processed / total) * 100) : INDETERMINATE;
}

/**
 * Rolls a set of percentages into one, ignoring {@link INDETERMINATE} members. Returns
 * {@link INDETERMINATE} when nothing is quantifiable.
 */
export function rollupPercentage(percentages: number[]): number {
  const determinate = percentages.filter(p => p !== INDETERMINATE);
  if (determinate.length === 0)
    return INDETERMINATE;

  const sum = determinate.reduce((acc, p) => acc + p, 0);
  return Math.round(sum / determinate.length);
}

/**
 * Rolls a set of activity statuses into a single group/overall status, in priority order:
 * any running ⇒ running, else any pending ⇒ pending, else any failed ⇒ failed, else all
 * cancelled ⇒ cancelled, else all skipped ⇒ skipped, else complete.
 *
 * The all-skipped arm is what keeps "nothing was configured to run" from reading as a success:
 * a mix of complete and skipped is a finished run, but skipping everything is not.
 */
export function rollupStatus(statuses: ActivityStatus[]): ActivityStatus {
  if (statuses.length === 0)
    return Status.COMPLETE;
  if (statuses.includes(Status.RUNNING))
    return Status.RUNNING;
  if (statuses.includes(Status.PENDING))
    return Status.PENDING;
  if (statuses.includes(Status.FAILED))
    return Status.FAILED;
  if (statuses.every(s => s === Status.CANCELLED))
    return Status.CANCELLED;
  if (statuses.every(s => s === Status.SKIPPED))
    return Status.SKIPPED;

  return Status.COMPLETE;
}
