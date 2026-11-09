/**
 * Why a backend request or task failed, as `rotkehlchen/errors/cause.py` spells it on the wire.
 *
 * @remarks
 * `UNKNOWN` is frontend-only: the answer did not name a cause, because it came from colibri or a
 * reverse proxy, there was no answer at all, or the value is newer than this build.
 */
export const FailureCause = {
  AUTH: 'auth',
  BAD_DATA: 'bad_data',
  CANCELLED: 'cancelled',
  CONFLICT: 'conflict',
  FORBIDDEN: 'forbidden',
  INTERNAL: 'internal',
  INVALID_INPUT: 'invalid_input',
  LOCAL_DB: 'local_db',
  NETWORK: 'network',
  NOT_FOUND: 'not_found',
  RATE_LIMITED: 'rate_limited',
  REMOTE_REJECTED: 'remote_rejected',
  UNKNOWN: 'unknown',
  UNSUPPORTED: 'unsupported',
} as const;

export type FailureCause = (typeof FailureCause)[keyof typeof FailureCause];

/** The field a failed backend answer names its cause in. */
export interface CarriesFailureCause {
  readonly cause?: unknown;
}

/** A record rather than a list, so a new cause does not compile until someone decides its retry. */
const RETRY_CAN_HELP: Record<FailureCause, boolean> = {
  [FailureCause.AUTH]: false,
  [FailureCause.BAD_DATA]: true,
  [FailureCause.CANCELLED]: false,
  [FailureCause.CONFLICT]: false,
  [FailureCause.FORBIDDEN]: false,
  [FailureCause.INTERNAL]: false,
  [FailureCause.INVALID_INPUT]: false,
  [FailureCause.LOCAL_DB]: false,
  [FailureCause.NETWORK]: true,
  [FailureCause.NOT_FOUND]: false,
  [FailureCause.RATE_LIMITED]: true,
  [FailureCause.REMOTE_REJECTED]: false,
  [FailureCause.UNKNOWN]: true,
  [FailureCause.UNSUPPORTED]: false,
};

const KNOWN_CAUSES = new Set<unknown>(Object.values(FailureCause));

function isFailureCause(value: unknown): value is FailureCause {
  return KNOWN_CAUSES.has(value);
}

/** Reads a cause off the wire, where anything but a known value counts as {@link FailureCause.UNKNOWN}. */
export function parseFailureCause(value: unknown): FailureCause {
  return isFailureCause(value) ? value : FailureCause.UNKNOWN;
}

/** Whether running the same request again could end differently, without the user changing anything. */
export function isRetryableCause(cause: FailureCause): boolean {
  return RETRY_CAN_HELP[cause];
}
