import { startPromise } from '@shared/utils';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { onSessionCleared } from '@/modules/core/session/session-lifecycle';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';

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
    catch (error: unknown) {
      if (!isRequestCancellation(error))
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
   * Forgets the session's scheduler state; the backend resets its own at logout.
   *
   * @remarks
   * Runs in the session's clear phase rather than at the start of a logout, so a fallback timer
   * armed by a session load that resumed after the logout is stopped too.
   */
  const reset = (): void => {
    stopFallbackTimer();
    set(schedulerEnabled, false);
  };

  onSessionCleared('scheduler-state', reset);

  return {
    onBalancesLoaded,
    onHistoryStarted,
    onHistoryFinished,
    reset,
  };
});
