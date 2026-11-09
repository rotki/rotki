import type { ScheduledJob } from './scheduler';
import type { ActivitySpec } from './spec';
import type { FailureCause } from '@/modules/core/api/failure-cause';
import { isTerminalStatus } from '../status';
import { type ActivityStatus, type ActivitySteps, ActivityStatus as Status } from '../types';

/**
 * One run of an activity, as the orchestrator tracks it.
 *
 * @remarks
 * A re-run gets a new record rather than a reset one (see {@link pendingRecord}), so every field
 * below describes the current run only.
 */
export interface ActivityRecord {
  readonly spec: ActivitySpec;
  status: ActivityStatus;
  steps?: ActivitySteps;
  startedAt?: number;
  /**
   * Why this activity failed or was skipped, in the producer's words. See `terminalReason` for
   * which outcomes get one.
   */
  reason?: string;
  /** Why this activity failed, in the backend's terms. See `terminalFailureCause`. */
  failureCause?: FailureCause;
  /** Whether a skip is held for the user. See `terminalAttention`. */
  attention?: true;
  /** Whether this run repeats an earlier one, rather than being a first submit. */
  readonly rerun: boolean;
  /** Set when the user cancelled a running activity; forces the terminal status to CANCELLED. */
  cancelRequested: boolean;
  /** Guards the spec's `cleanup` to fire once per run. */
  cleanedUp: boolean;
  /** The scheduler job of this run, so a running cancel can release its lane slot. */
  job?: ScheduledJob;
}

/** A record for a run that has not started yet, for a first submit and for a re-run alike. */
export function pendingRecord(spec: ActivitySpec, rerun = false): ActivityRecord {
  return { cancelRequested: false, cleanedUp: false, rerun, spec, status: Status.PENDING };
}

/**
 * Cancels every run still going and fires its cleanup, for a session ending. A run already settled,
 * or already cleaned up, is left as it is.
 */
export function abandonLive(records: Iterable<ActivityRecord>): void {
  for (const record of records) {
    if (isTerminalStatus(record.status) || record.cleanedUp)
      continue;
    record.status = Status.CANCELLED;
    record.cleanedUp = true;
    record.spec.cleanup?.();
  }
}
