import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceRefreshScheduler } from './use-balance-refresh-scheduler';

interface SchedulerOptions {
  callback: () => void;
  intervalMs: number;
}

let capturedOptions: SchedulerOptions | undefined;
const schedulerStart = vi.fn();
const schedulerStop = vi.fn();

const canRequestData = ref<boolean>(false);
const refreshPeriod = ref<number>(0);
const autoRefresh = vi.fn().mockResolvedValue(undefined);

vi.mock('./use-interval-scheduler', () => ({
  useIntervalScheduler: (options: SchedulerOptions): object => {
    capturedOptions = options;
    return { start: schedulerStart, stop: schedulerStop };
  },
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ canRequestData }),
}));

vi.mock('@/modules/settings/use-frontend-settings-store', () => ({
  useFrontendSettingsStore: (): object => ({ refreshPeriod }),
}));

vi.mock('@/modules/balances/use-balance-fetching', () => ({
  useBalanceFetching: (): object => ({ autoRefresh }),
}));

describe('useBalanceRefreshScheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOptions = undefined;
    set(canRequestData, false);
    set(refreshPeriod, 0);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should convert the refresh period from minutes to milliseconds', () => {
    set(refreshPeriod, 5);
    useBalanceRefreshScheduler();
    expect(capturedOptions?.intervalMs).toBe(5 * 60 * 1000);
  });

  it('should floor the interval at 1ms when the period is zero', () => {
    set(refreshPeriod, 0);
    useBalanceRefreshScheduler();
    expect(capturedOptions?.intervalMs).toBe(1);
  });

  it('should auto refresh when data can be requested', () => {
    set(canRequestData, true);
    useBalanceRefreshScheduler();
    capturedOptions?.callback();
    expect(autoRefresh).toHaveBeenCalledOnce();
  });

  it('should not auto refresh when data cannot be requested', () => {
    set(canRequestData, false);
    useBalanceRefreshScheduler();
    capturedOptions?.callback();
    expect(autoRefresh).not.toHaveBeenCalled();
  });

  it('should start the scheduler when the period is positive', () => {
    set(refreshPeriod, 5);
    useBalanceRefreshScheduler().start();
    expect(schedulerStart).toHaveBeenCalledOnce();
  });

  it('should not start the scheduler when the period is zero', () => {
    set(refreshPeriod, 0);
    useBalanceRefreshScheduler().start();
    expect(schedulerStart).not.toHaveBeenCalled();
  });

  it('should not start when auto fetch is disabled via env', () => {
    vi.stubEnv('VITE_NO_AUTO_FETCH', 'true');
    set(refreshPeriod, 5);
    useBalanceRefreshScheduler().start();
    expect(schedulerStart).not.toHaveBeenCalled();
  });

  it('should delegate stop to the interval scheduler', () => {
    useBalanceRefreshScheduler().stop();
    expect(schedulerStop).toHaveBeenCalledOnce();
  });
});
