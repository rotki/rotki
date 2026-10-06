import { startPromise } from '@shared/utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope, nextTick } from 'vue';
import { beginSession, endSession } from '@/modules/core/session/session-lifecycle';
import { useSessionStateCleaner } from './use-session-state-cleaner';

const logged = ref<boolean>(false);
const clearUploadStatus = vi.fn();
const start = vi.fn();
const stop = vi.fn();
const reset = vi.fn();
const resetState = vi.fn();
const resetNativeTasks = vi.fn();
const resetAccountLoad = vi.fn();
const resetHydration = vi.fn();

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ logged }),
}));

vi.mock('@/modules/session/use-session-sync', () => ({
  useSync: (): object => ({ clearUploadStatus }),
}));

vi.mock('@/modules/shell/app/use-monitor-service', () => ({
  useMonitorService: (): object => ({ start, stop }),
}));

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: (): object => ({ reset }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): object => ({ reset: resetNativeTasks }),
}));

vi.mock('@/modules/accounts/use-account-load-state', () => ({
  useAccountLoadState: (): object => ({ reset: resetAccountLoad }),
}));

vi.mock('@/modules/balances/use-balance-hydration', () => ({
  useBalanceHydration: (): object => ({ reset: resetHydration }),
}));

vi.mock('@/modules/shell/app/store-plugins', () => ({
  resetState: (): void => resetState(),
}));

/** Lets the clear phase, which follows the end of a session by one task, run. */
async function nextTask(): Promise<void> {
  await vi.advanceTimersByTimeAsync(0);
}

describe('useSessionStateCleaner', () => {
  let scope: EffectScope;

  beforeEach(() => {
    vi.useFakeTimers();
    set(logged, false);
    scope = effectScope();
    scope.run(() => useSessionStateCleaner());
    beginSession();
    vi.clearAllMocks();
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it('should start the monitor when the user logs in', async () => {
    set(logged, true);
    await nextTick();
    expect(start).toHaveBeenCalledOnce();
    expect(stop).not.toHaveBeenCalled();
  });

  it('should stop the session\'s work when the user logs out, before clearing anything', async () => {
    set(logged, true);
    await nextTick();
    set(logged, false);
    await nextTick();

    expect(stop).toHaveBeenCalledOnce();
    expect(reset).toHaveBeenCalledOnce();
    expect(resetNativeTasks).toHaveBeenCalledOnce();
    expect(resetAccountLoad).toHaveBeenCalledOnce();
    expect(resetHydration).toHaveBeenCalledOnce();
    expect(reset.mock.invocationCallOrder[0]).toBeLessThan(resetNativeTasks.mock.invocationCallOrder[0]);
    expect(resetState).not.toHaveBeenCalled();
    expect(clearUploadStatus).not.toHaveBeenCalled();
  });

  it('should clear the session\'s state one task after the logout, once its callers have resumed', async () => {
    const writtenBeforeReset: string[] = [];
    set(logged, true);
    await nextTick();
    set(logged, false);
    await nextTick();
    startPromise((async (): Promise<void> => {
      await Promise.resolve();
      writtenBeforeReset.push(resetState.mock.calls.length === 0 ? 'before' : 'after');
    })());

    await nextTask();

    expect(clearUploadStatus).toHaveBeenCalledOnce();
    expect(resetState).toHaveBeenCalledOnce();
    expect(writtenBeforeReset).toEqual(['before']);
  });

  it('should stop the work but keep the state when a session ends without a logout, as a failed unlock does', async () => {
    endSession();
    await nextTask();

    expect(reset).toHaveBeenCalledOnce();
    expect(resetState).not.toHaveBeenCalled();
    expect(clearUploadStatus).not.toHaveBeenCalled();
  });

  it('should neither stop nor clear anything while the user stays logged in', async () => {
    set(logged, true);
    await nextTick();
    await nextTask();
    expect(stop).not.toHaveBeenCalled();
    expect(reset).not.toHaveBeenCalled();
    expect(resetNativeTasks).not.toHaveBeenCalled();
    expect(resetHydration).not.toHaveBeenCalled();
    expect(resetState).not.toHaveBeenCalled();
  });
});
