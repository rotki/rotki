/** Wait between requests: about three a minute. */
export const REQUEST_DELAY_MS = 20_000;

/** First wait after a rate limit, doubled on each one that follows. */
export const BACKOFF_START_MS = 60_000;

/** The longest wait after repeated rate limits. */
export const BACKOFF_MAX_MS = 15 * 60_000;

export interface Pacing {
  /** How long to wait before the next request, in milliseconds. */
  readonly delay: number;
  /** The backoff to double on the next rate limit; zero once a request goes through. */
  readonly backoff: number;
}

/**
 * The wait before the next backfill request.
 *
 * @remarks
 * A rate limit doubles the wait each time it repeats, up to {@link BACKOFF_MAX_MS}. A request that
 * goes through resets the backoff, and the next wait is the normal pace.
 *
 * @param rateLimited - whether the last request hit a rate limit or failed
 * @param backoff - the backoff the previous request left
 */
export function nextPacing(rateLimited: boolean, backoff: number): Pacing {
  if (rateLimited) {
    const next = backoff === 0 ? BACKOFF_START_MS : Math.min(BACKOFF_MAX_MS, backoff * 2);
    return { backoff: next, delay: next };
  }
  return { backoff: 0, delay: REQUEST_DELAY_MS };
}
