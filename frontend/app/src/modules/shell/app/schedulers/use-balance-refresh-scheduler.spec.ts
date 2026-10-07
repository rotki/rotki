import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceRefreshScheduler } from './use-balance-refresh-scheduler';

const MINUTE = 60 * 1000;

const canRequestData = ref<boolean>(true);
const refreshPeriod = ref<number>(-1);
const autoRefresh = vi.fn<() => Promise<void>>();

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ canRequestData }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'refreshPeriod' ? refreshPeriod : ref(undefined))),
}));

vi.mock('@/modules/balances/use-balance-fetching', () => ({
  useBalanceFetching: (): object => ({ autoRefresh }),
}));

describe('useBalanceRefreshScheduler', () => {
  let scope: ReturnType<typeof effectScope>;

  function startScheduler(): ReturnType<typeof useBalanceRefreshScheduler> {
    const scheduler = scope.run(() => useBalanceRefreshScheduler());
    assert(scheduler);
    scheduler.start();
    return scheduler;
  }

  async function changePeriod(minutes: number): Promise<void> {
    set(refreshPeriod, minutes);
    await nextTick();
  }

  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    autoRefresh.mockResolvedValue(undefined);
    scope = effectScope();
    set(canRequestData, true);
    set(refreshPeriod, -1);
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
    vi.unstubAllEnvs();
  });

  it('should refresh once per refresh period', async () => {
    set(refreshPeriod, 30);
    startScheduler();

    await vi.advanceTimersByTimeAsync(30 * MINUTE);
    expect(autoRefresh).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(30 * MINUTE);
    expect(autoRefresh).toHaveBeenCalledTimes(2);
  });

  it('should stay idle while the refresh period is disabled', async () => {
    startScheduler();

    await vi.advanceTimersByTimeAsync(24 * 60 * MINUTE);

    expect(autoRefresh).not.toHaveBeenCalled();
  });

  it('should start refreshing when the period is enabled after the scheduler started', async () => {
    startScheduler();

    await changePeriod(30);
    await vi.advanceTimersByTimeAsync(30 * MINUTE);

    expect(autoRefresh).toHaveBeenCalledOnce();
  });

  it('should follow a period change while running', async () => {
    set(refreshPeriod, 60);
    startScheduler();

    await changePeriod(30);
    await vi.advanceTimersByTimeAsync(30 * MINUTE);

    expect(autoRefresh).toHaveBeenCalledOnce();
  });

  it('should stop refreshing when the period is disabled while running', async () => {
    set(refreshPeriod, 30);
    startScheduler();

    await changePeriod(-1);
    await vi.advanceTimersByTimeAsync(60 * MINUTE);

    expect(autoRefresh).not.toHaveBeenCalled();
  });

  it('should not arm on a period change after it was stopped', async () => {
    set(refreshPeriod, 30);
    startScheduler().stop();

    await changePeriod(5);
    await vi.advanceTimersByTimeAsync(60 * MINUTE);

    expect(autoRefresh).not.toHaveBeenCalled();
  });

  it('should skip a tick while data cannot be requested', async () => {
    set(refreshPeriod, 30);
    set(canRequestData, false);
    startScheduler();

    await vi.advanceTimersByTimeAsync(30 * MINUTE);

    expect(autoRefresh).not.toHaveBeenCalled();
  });

  it('should not start when auto fetch is disabled via env', async () => {
    vi.stubEnv('VITE_NO_AUTO_FETCH', 'true');
    set(refreshPeriod, 30);
    startScheduler();

    await vi.advanceTimersByTimeAsync(30 * MINUTE);

    expect(autoRefresh).not.toHaveBeenCalled();
  });
});
