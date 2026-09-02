export interface CombinedAbortSignal {
  signal: AbortSignal;
  /** Clears the timeout timer. Must be called once the request settles. */
  dispose: () => void;
}

/**
 * Combines the api-wide abort signal with a request's own and its timeout, so a request can be
 * cancelled from any of the three.
 *
 * @remarks
 * The timeout has to be composed here: ofetch honours its own `timeout` option only when no signal
 * is passed, and every call site passes one. Combine per attempt, so a retry gets its own budget.
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
