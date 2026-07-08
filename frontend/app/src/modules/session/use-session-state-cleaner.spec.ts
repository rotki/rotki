import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope, nextTick } from 'vue';
import { useSessionStateCleaner } from './use-session-state-cleaner';

const logged = ref<boolean>(false);
const clearUploadStatus = vi.fn();
const start = vi.fn();
const stop = vi.fn();
const resetInstance = vi.fn();
const resetState = vi.fn();

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ logged }),
}));

vi.mock('@/modules/session/use-session-sync', () => ({
  useSync: (): object => ({ clearUploadStatus }),
}));

vi.mock('@/modules/shell/app/use-monitor-service', () => ({
  useMonitorService: (): object => ({ start, stop }),
}));

vi.mock('@/modules/balances/services/balance-queue', () => ({
  BalanceQueueService: { resetInstance: (): void => resetInstance() },
}));

vi.mock('@/modules/shell/app/store-plugins', () => ({
  resetState: (): void => resetState(),
}));

describe('useSessionStateCleaner', () => {
  let scope: EffectScope;

  beforeEach(() => {
    vi.clearAllMocks();
    set(logged, false);
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
  });

  it('should start the monitor when the user logs in', async () => {
    scope.run(() => useSessionStateCleaner());
    set(logged, true);
    await nextTick();
    expect(start).toHaveBeenCalledOnce();
    expect(stop).not.toHaveBeenCalled();
  });

  it('should stop the monitor and run cleanup when the user logs out', async () => {
    set(logged, true);
    scope.run(() => useSessionStateCleaner());
    set(logged, false);
    await nextTick();
    expect(stop).toHaveBeenCalledOnce();
    expect(clearUploadStatus).toHaveBeenCalledOnce();
    expect(resetInstance).toHaveBeenCalledOnce();
    expect(resetState).toHaveBeenCalledOnce();
  });

  it('should not clean up while the user stays logged in', async () => {
    scope.run(() => useSessionStateCleaner());
    set(logged, true);
    await nextTick();
    expect(clearUploadStatus).not.toHaveBeenCalled();
    expect(resetState).not.toHaveBeenCalled();
  });
});
