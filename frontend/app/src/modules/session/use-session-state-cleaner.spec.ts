import type { RotkiApi } from '@/modules/core/api/rotki-api';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope, nextTick } from 'vue';
import { BALANCE_HYDRATION_TAG } from '@/modules/balances/api/use-blockchain-balances-api';
import { SUGGESTION_PROBE_TAG } from '@/modules/settings/suggestions/use-suggestion-probes';
import { useSessionStateCleaner } from './use-session-state-cleaner';

const logged = ref<boolean>(false);
const clearUploadStatus = vi.fn();
const start = vi.fn();
const stop = vi.fn();
const reset = vi.fn();
const resetState = vi.fn();
const cancelByTag = vi.fn();
const resetNativeTasks = vi.fn();
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

vi.mock('@/modules/balances/use-balance-hydration', () => ({
  useBalanceHydration: (): object => ({ reset: resetHydration }),
}));

vi.mock('@/modules/shell/app/store-plugins', () => ({
  resetState: (): void => resetState(),
}));

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: createMock<RotkiApi>({ cancelByTag: (tag: string): void => cancelByTag(tag) }),
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
    expect(reset).toHaveBeenCalledOnce();
    expect(resetNativeTasks).toHaveBeenCalledOnce();
    expect(resetHydration).toHaveBeenCalledOnce();
    expect(resetState).toHaveBeenCalledOnce();
    expect(cancelByTag).toHaveBeenCalledWith(SUGGESTION_PROBE_TAG);
    expect(cancelByTag).toHaveBeenCalledWith(BALANCE_HYDRATION_TAG);
    expect(cancelByTag.mock.invocationCallOrder.at(-1))
      .toBeLessThan(resetHydration.mock.invocationCallOrder[0]);
  });

  it('should not clean up while the user stays logged in', async () => {
    scope.run(() => useSessionStateCleaner());
    set(logged, true);
    await nextTick();
    expect(clearUploadStatus).not.toHaveBeenCalled();
    expect(reset).not.toHaveBeenCalled();
    expect(resetNativeTasks).not.toHaveBeenCalled();
    expect(resetHydration).not.toHaveBeenCalled();
    expect(resetState).not.toHaveBeenCalled();
  });
});
