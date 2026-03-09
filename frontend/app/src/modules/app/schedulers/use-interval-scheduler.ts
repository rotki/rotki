import { startPromise } from '@shared/utils';

interface UseIntervalSchedulerOptions {
  /** The callback to invoke on each tick */
  callback: () => Promise<void> | void;
  /** Interval period in milliseconds */
  intervalMs: number;
}

interface UseIntervalSchedulerReturn {
  start: (immediate?: boolean) => void;
  stop: () => void;
}

/**
 * Creates a managed setInterval scheduler with start/stop lifecycle.
 * Prevents double-start and cleans up on scope dispose.
 */
export function useIntervalScheduler(options: UseIntervalSchedulerOptions): UseIntervalSchedulerReturn {
  let intervalId: NodeJS.Timeout | undefined;

  function start(immediate = false): void {
    if (intervalId)
      return;

    if (immediate)
      startPromise(Promise.resolve(options.callback()));

    intervalId = setInterval(() => startPromise(Promise.resolve(options.callback())), options.intervalMs);
  }

  function stop(): void {
    if (!intervalId)
      return;

    clearInterval(intervalId);
    intervalId = undefined;
  }

  onScopeDispose(stop);

  return { start, stop };
}
