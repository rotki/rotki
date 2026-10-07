import type { MaybeRefOrGetter } from 'vue';
import { startPromise } from '@shared/utils';

interface UseIntervalSchedulerOptions {
  /** The callback to invoke on each tick */
  callback: () => Promise<void> | void;
  /** Interval period in milliseconds; zero or less leaves a started scheduler idle until it turns positive */
  intervalMs: MaybeRefOrGetter<number>;
}

interface UseIntervalSchedulerReturn {
  start: (immediate?: boolean) => void;
  stop: () => void;
}

/**
 * Creates a managed setInterval scheduler with start/stop lifecycle.
 * Prevents double-start and cleans up on scope dispose.
 *
 * @remarks
 * A started scheduler re-arms when `intervalMs` changes, so a period read from a setting follows
 * the setting instead of keeping the value it had when the scheduler was built.
 */
export function useIntervalScheduler(options: UseIntervalSchedulerOptions): UseIntervalSchedulerReturn {
  let intervalId: NodeJS.Timeout | undefined;
  let started = false;

  function tick(): void {
    startPromise(Promise.resolve(options.callback()));
  }

  function arm(): void {
    const intervalMs = toValue(options.intervalMs);
    if (intervalMs > 0)
      intervalId = setInterval(tick, intervalMs);
  }

  function disarm(): void {
    clearInterval(intervalId);
    intervalId = undefined;
  }

  function start(immediate = false): void {
    if (started)
      return;

    started = true;
    if (immediate)
      tick();

    arm();
  }

  function stop(): void {
    started = false;
    disarm();
  }

  watch(() => toValue(options.intervalMs), () => {
    if (!started)
      return;

    disarm();
    arm();
  });

  onScopeDispose(stop);

  return { start, stop };
}
