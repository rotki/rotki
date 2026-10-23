import type { ScheduledJob } from './scheduler';
import type { ActivitySpec } from './spec';
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
  /** Whether a skip is held for the user. See `terminalAttention`. */
  attention?: true;
  /** Set when the user cancelled a running activity; forces the terminal status to CANCELLED. */
  cancelRequested: boolean;
  /** Guards the spec's `cleanup` to fire once per run. */
  cleanedUp: boolean;
  /** The scheduler job of this run, so a running cancel can release its lane slot. */
  job?: ScheduledJob;
}

/** A record for a run that has not started yet, for a first submit and for a re-run alike. */
export function pendingRecord(spec: ActivitySpec): ActivityRecord {
  return { cancelRequested: false, cleanedUp: false, spec, status: Status.PENDING };
}
