import type { EffectScope } from 'vue';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { logger } from '@/modules/core/common/logging/logging';

const mockSetSchedulerState = vi.fn();

vi.mock('@/modules/core/tasks/use-task-api', () => ({
  useTaskApi: vi.fn(() => ({
    setSchedulerState: mockSetSchedulerState,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
  },
}));

/** Matches TEN_MINUTES_MS in use-scheduler-state.ts */
const TEN_MINUTES_MS = 10 * 60 * 1000;

describe('composables::session::use-scheduler-state', () => {
  let scope: EffectScope;

  async function createSchedulerState(): Promise<ReturnType<typeof import('@/modules/session/use-scheduler-state.ts').useSchedulerState>> {
    const { useSchedulerState } = await import('@/modules/session/use-scheduler-state.ts');
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

      expect(mockSetSchedulerState).not.toHaveBeenCalled();

      vi.advanceTimersByTime(TEN_MINUTES_MS);
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should not start fallback timer if scheduler is already enabled', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
      mockSetSchedulerState.mockClear();

      scheduler.onBalancesLoaded();

      vi.advanceTimersByTime(TEN_MINUTES_MS);
      await flushPromises();

      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });
  });

  describe('onHistoryStarted', () => {
    it('should stop fallback timer', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      vi.advanceTimersByTime(TEN_MINUTES_MS / 2);

      scheduler.onHistoryStarted();

      vi.advanceTimersByTime(TEN_MINUTES_MS);
      await flushPromises();

      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });
  });

  describe('onHistoryFinished', () => {
    it('should enable scheduler', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledTimes(1);
      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should stop fallback timer when enabling scheduler', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledTimes(1);
      mockSetSchedulerState.mockClear();

      vi.advanceTimersByTime(TEN_MINUTES_MS);
      await flushPromises();

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

    it('should enable scheduler after onHistoryStarted', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryStarted();
      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
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

      scheduler.onBalancesLoaded();

      scheduler.reset();

      vi.advanceTimersByTime(TEN_MINUTES_MS);
      await flushPromises();

      expect(mockSetSchedulerState).not.toHaveBeenCalled();
    });

    it('should reset scheduler enabled state', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
      mockSetSchedulerState.mockClear();

      scheduler.reset();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });
  });

  describe('fallback timeout', () => {
    it('should enable scheduler after 10 minutes', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      vi.advanceTimersByTime(TEN_MINUTES_MS - 1);
      await flushPromises();

      expect(mockSetSchedulerState).not.toHaveBeenCalled();

      vi.advanceTimersByTime(1);
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should handle error when fallback timer enables scheduler', async () => {
      mockSetSchedulerState.mockRejectedValueOnce(new Error('API Error'));

      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      vi.advanceTimersByTime(TEN_MINUTES_MS);
      await flushPromises();

      expect(logger.error).toHaveBeenCalledWith('Failed to enable task scheduler:', expect.any(Error));
    });
  });

  describe('typical flow', () => {
    it('should handle normal startup flow: balances loaded -> history started -> history finished', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();
      expect(mockSetSchedulerState).not.toHaveBeenCalled();

      scheduler.onHistoryStarted();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should handle flow when user never visits history page', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onBalancesLoaded();

      vi.advanceTimersByTime(TEN_MINUTES_MS);
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
    });

    it('should handle logout and re-login', async () => {
      const scheduler = await createSchedulerState();

      scheduler.onHistoryFinished();
      await flushPromises();

      expect(mockSetSchedulerState).toHaveBeenCalledWith(true);
      mockSetSchedulerState.mockClear();

      scheduler.reset();

      scheduler.onBalancesLoaded();

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
});
