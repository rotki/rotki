import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEvmStatusScheduler } from './use-evm-status-scheduler';

interface SchedulerOptions {
  callback: () => void;
  intervalMs: number;
}

let capturedOptions: SchedulerOptions | undefined;
const schedulerStart = vi.fn();
const schedulerStop = vi.fn();

const canRequestData = ref<boolean>(false);
const fetchTransactionStatusSummary = vi.fn().mockResolvedValue(undefined);

vi.mock('./use-interval-scheduler', () => ({
  useIntervalScheduler: (options: SchedulerOptions): object => {
    capturedOptions = options;
    return { start: schedulerStart, stop: schedulerStop };
  },
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ canRequestData }),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: (): object => ({ fetchTransactionStatusSummary }),
}));

describe('useEvmStatusScheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOptions = undefined;
    set(canRequestData, false);
  });

  it('should poll every ten minutes', () => {
    useEvmStatusScheduler();
    expect(capturedOptions?.intervalMs).toBe(10 * 60 * 1000);
  });

  it('should fetch the status summary when data can be requested', () => {
    set(canRequestData, true);
    useEvmStatusScheduler();
    capturedOptions?.callback();
    expect(fetchTransactionStatusSummary).toHaveBeenCalledOnce();
  });

  it('should not fetch when data cannot be requested', () => {
    set(canRequestData, false);
    useEvmStatusScheduler();
    capturedOptions?.callback();
    expect(fetchTransactionStatusSummary).not.toHaveBeenCalled();
  });

  it('should start immediately when data can already be requested', () => {
    set(canRequestData, true);
    useEvmStatusScheduler().start();
    expect(schedulerStart).toHaveBeenCalledWith(true);
  });

  it('should delegate stop to the interval scheduler', () => {
    useEvmStatusScheduler().stop();
    expect(schedulerStop).toHaveBeenCalledOnce();
  });
});
