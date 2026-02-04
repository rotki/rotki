import { startPromise } from '@shared/utils';
import { useTaskApi } from '@/composables/api/task';
import { logger } from '@/utils/logging';

/**
 * Fallback timeout to enable scheduler if user hasn't visited history page.
 * After this duration, the scheduler will be enabled regardless of history status.
 */
const TEN_MINUTES_MS = 10 * 60 * 1000;

interface UseSchedulerStateReturn {
  onBalancesLoaded: () => void;
  onHistoryStarted: () => void;
  onHistoryFinished: () => void;
  reset: () => void;
}

/**
 * Manages the backend task scheduler state.
 *
 * The scheduler is disabled during startup to avoid running automated tasks
 * in parallel with user-initiated tasks. It gets enabled either:
 * 1. When history loading finishes (via onHistoryFinished)
 * 2. After a 10-minute fallback timeout if user never visits history page
 */
export const useSchedulerState = createSharedComposable((): UseSchedulerStateReturn => {
  const { setSchedulerState } = useTaskApi();

  const schedulerEnabled = ref<boolean>(false);

  const enableScheduler = async (): Promise<void> => {
    if (get(schedulerEnabled))
      return;

    try {
      await setSchedulerState(true);
      set(schedulerEnabled, true);
      logger.info('Task scheduler enabled');
    }
    catch (error: any) {
      logger.error('Failed to enable task scheduler:', error);
    }
  };

  const { start: startFallbackTimer, stop: stopFallbackTimer } = useTimeoutFn(
    () => startPromise(enableScheduler()),
    TEN_MINUTES_MS,
    { immediate: false },
  );

  /**
   * Called after balances finish loading - start fallback timer
   */
  const onBalancesLoaded = (): void => {
    if (!get(schedulerEnabled)) {
      startFallbackTimer();
    }
  };

  /**
   * Called when history starts - cancel fallback timer
   */
  const onHistoryStarted = (): void => {
    stopFallbackTimer();
  };

  /**
   * Called when history finishes - enable scheduler
   */
  const onHistoryFinished = (): void => {
    stopFallbackTimer();
    startPromise(enableScheduler());
  };

  /**
   * Called on logout - reset state (backend resets scheduler separately)
   */
  const reset = (): void => {
    stopFallbackTimer();
    set(schedulerEnabled, false);
  };

  return {
    onBalancesLoaded,
    onHistoryStarted,
    onHistoryFinished,
    reset,
  };
});
