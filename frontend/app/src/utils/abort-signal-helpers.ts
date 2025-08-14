export function combineAbortSignals(signals: (AbortSignal | undefined)[]): AbortSignal {
  const validSignals = signals.filter((signal): signal is AbortSignal => signal !== undefined);

  if (validSignals.length === 0) {
    return new AbortController().signal;
  }

  if (validSignals.length === 1) {
    return validSignals[0];
  }

  return AbortSignal.any(validSignals);
}

export function createTimeoutSignal(timeoutMs: number): AbortSignal {
  const controller = new AbortController();
  setTimeout(() => controller.abort(), timeoutMs);
  return controller.signal;
}

export function withTimeout(signal: AbortSignal | undefined, timeoutMs: number): AbortSignal {
  const timeoutSignal = createTimeoutSignal(timeoutMs);
  return combineAbortSignals([signal, timeoutSignal]);
}
