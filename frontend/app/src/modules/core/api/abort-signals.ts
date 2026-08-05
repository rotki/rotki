export interface CombinedAbortSignal {
  signal: AbortSignal;
  /** Clears the timeout timer. Must be called once the request settles. */
  dispose: () => void;
}

/**
 * Combines the api-wide abort signal with a request's own and its timeout, so a request can be
 * cancelled from any of the three.
 *
 * Only the api-wide one used to reach the fetch. The queue attached a per-request signal that was
 * then overwritten, which made `cancelById`/`cancelByTag` reject the caller's promise while the
 * connection kept running to completion; the queue freed the slot at the same time, so it could
 * dispatch a replacement and oversubscribe the browser's own per-host connection limit.
 *
 * The timeout is composed here rather than left to ofetch, which only honours its `timeout` option
 * when no signal is passed (`!context.options.signal && context.options.timeout`). Every call site
 * passes one, so no request in the app was ever actually bounded by it.
 *
 * `setTimeout` rather than `AbortSignal.timeout`: the timer has to be clearable when the request
 * settles first, or every request leaves one pending for its whole timeout - up to ten minutes for
 * a download. It also keeps the behaviour reachable from tests, which fake the clock. Callers
 * combine per attempt, so a retry gets its own budget rather than inheriting the first one's.
 */
export function combineAbortSignals(
  shared: AbortSignal,
  request?: AbortSignal | null,
  timeoutMs?: number,
): CombinedAbortSignal {
  const signals: AbortSignal[] = [shared];

  if (request)
    signals.push(request);

  if (timeoutMs === undefined || timeoutMs <= 0) {
    return {
      dispose: (): void => {},
      signal: signals.length === 1 ? shared : AbortSignal.any(signals),
    };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => {
    const error = new DOMException(`Request timed out after ${timeoutMs}ms`, 'TimeoutError');
    controller.abort(error);
  }, timeoutMs);
  signals.push(controller.signal);

  return {
    dispose: (): void => {
      clearTimeout(timer);
    },
    signal: AbortSignal.any(signals),
  };
}
