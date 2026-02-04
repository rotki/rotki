import type { EffectScope } from 'vue';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { logger } from '@/utils/logging';

const mockSetSchedulerState = vi.fn();

vi.mock('@/composables/api/task', () => ({
  useTaskApi: vi.fn(() => ({
    setSchedulerState: mockSetSchedulerState,
  })),
}));

vi.mock('@/utils/logging', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
  },
}));

describe('composables::session::use-scheduler-state', () => {
  let scope: EffectScope;

  async function createSchedulerState(): Promise<ReturnType<typeof import('@/composables/session/use-scheduler-state.ts').useSchedulerState>> {
    const { useSchedulerState } = await import('@/composables/session/use-scheduler-state.ts');
    return scope.run(() => useSchedulerState())!;
  }

  beforeEach(() => {
    vi.useFakeTimers();
    const pinia = createPinia();
    setActivePinia(pinia);
    scope = effectScope();

    mockSetSchedulerState.mockResolvedValue(undefined);
  });

  afterEach(() => {
    scope.stop();
    vi.clearAllMocks();
    vi.useRealTimers();
    vi.resetModules();
  });

  describe('onBalancesLoaded', () => {
    it('should start fallback timer when scheduler is not enabled', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      // Timer should not have fired yet
      expect(mockSetSchedulerState).not.toHaveBeenCalled();

      // Advance time by 10 minutes
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should not start fallback timer if scheduler is already enabled', async () => {
      const scheduler = await createSchedulerState();

      // Enable scheduler first via onHistoryFinished
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
      mockSetSchedulerState.mockClear();

      // Now call onBalancesLoaded
      scheduler.onBalancesLoaded();

      // Advance time by 10 minutes
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      // Should not call setSchedulerState again
      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });
  });

  describe('onHistoryStarted', () => {
    it('should stop fallback timer', async () => {
      const scheduler = await createSchedulerState();

      // Start fallback timer
      scheduler.onBalancesLoaded();

      // Advance time partially
      vi.advanceTimersByTime(5 * 60 * 1000);

      // Cancel the timer by calling onHistoryStarted
      scheduler.onHistoryStarted();

      // Advance past the original timeout
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      // Scheduler should not have been enabled via fallback
      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });
  });

  describe('onHistoryFinished', () => {
    it('should enable scheduler', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should stop fallback timer when enabling scheduler', async () => {
      const scheduler = await createSchedulerState();

      // Start fallback timer
      scheduler.onBalancesLoaded();

      // Enable scheduler via history finished
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledTimes(1);
      mockSetSchedulerState.mockClear();

      // Advance past fallback timeout
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      // Should not call again
      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });

    it('should not enable scheduler twice if already enabled', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledTimes(1);

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledTimes(1);
    });

    it('should handle error when enabling scheduler fails', async () => {
      mockSetSchedulerState.mockRejectedValueOnce(new Error('API Error'));

      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(logger.error).toHaveBeenCalledWith('Failed to enable task scheduler:', expect.any(Error));
    });
  });

  describe('reset', () => {
    it('should stop fallback timer', async () => {
      const scheduler = await createSchedulerState();

      // Start fallback timer
      scheduler.onBalancesLoaded();

      // Reset
      scheduler.reset();

      // Advance past timeout
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });

    it('should reset scheduler enabled state', async () => {
      const scheduler = await createSchedulerState();

      // Enable scheduler
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
      mockSetSchedulerState.mockClear();

      // Reset
      scheduler.reset();

      // Now onHistoryFinished should enable again
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });
  });

  describe('fallback timeout', () => {
    it('should enable scheduler after 10 minutes', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      // Advance time by just under 10 minutes
      vi.advanceTimersByTime(10 * 60 * 1000 - 1);
      await flushPromises();

      expect(mockSetSchedulerState).not.toHaveBeenCalled();

      // Advance the remaining time
      vi.advanceTimersByTime(1);
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should handle error when fallback timer enables scheduler', async () => {
      mockSetSchedulerState.mockRejectedValueOnce(new Error('API Error'));

      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      expect(logger.error).toHaveBeenCalledWith('Failed to enable task scheduler:', expect.any(Error));
    });
  });

  describe('typical flow', () => {
    it('should handle normal startup flow: balances loaded -> history started -> history finished', async () => {
      const scheduler = await createSchedulerState();

      // Balances finish loading, start fallback timer
      scheduler.onBalancesLoaded();
      expect(mockSetSchedulerState).not.toHaveBeenCalled();

      // History starts, cancel fallback timer
      scheduler.onHistoryStarted();

      // History finishes, enable scheduler
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should handle flow when user never visits history page', async () => {
      const scheduler = await createSchedulerState();

      // Balances finish loading, start fallback timer
      scheduler.onBalancesLoaded();

      // User never visits history, wait for fallback
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should handle logout and re-login', async () => {
      const scheduler = await createSchedulerState();

      // First session: enable scheduler
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
      mockSetSchedulerState.mockClear();

      // Logout
      scheduler.reset();

      // New session: balances loaded
      scheduler.onBalancesLoaded();

      // History finished
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });
  });

  describe('logging', () => {
    it('should log info when scheduler is enabled', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(logger.info).toHaveBeenCalledWith('Task scheduler enabled');
    });
  });

  describe('trigger functions call expected behavior', () => {
    it('onBalancesLoaded triggers fallback timer to start', async () => {
      const scheduler = await createSchedulerState();

      // Call the trigger
      scheduler.onBalancesLoaded();

      // Verify timer was started by checking it fires after 10 minutes
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('onHistoryStarted triggers fallback timer to stop', async () => {
      const scheduler = await createSchedulerState();

      // Start the timer first
      scheduler.onBalancesLoaded();

      // Call the trigger to stop
      scheduler.onHistoryStarted();

      // Verify timer was stopped - it should not fire
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();

      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });

    it('onHistoryFinished triggers setSchedulerState to be called with true', async () => {
      const scheduler = await createSchedulerState();

      // Call the trigger
      scheduler.onHistoryFinished();
      await flushPromises();

      // Verify setSchedulerState was called
      expect(mockSetSchedulerState).toHaveBeenCalledTimes(1);
      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('reset triggers fallback timer to stop and resets internal state', async () => {
      const scheduler = await createSchedulerState();

      // Enable scheduler first
      scheduler.onHistoryFinished();
      await flushPromises();
      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
      mockSetSchedulerState.mockClear();

      // Start fallback timer
      scheduler.onBalancesLoaded();

      // Call reset trigger
      scheduler.reset();

      // Verify timer was stopped
      vi.advanceTimersByTime(10 * 60 * 1000);
      await flushPromises();
      expect(mockSetSchedulerState).not.toHaveBeenCalled();

      // Verify internal state was reset - onHistoryFinished should enable again
      scheduler.onHistoryFinished();
      await flushPromises();
      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('onHistoryFinished after onHistoryStarted triggers scheduler enable', async () => {
      const scheduler = await createSchedulerState();

      // Typical flow: start then finish
      scheduler.onHistoryStarted();
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });
  });
});
