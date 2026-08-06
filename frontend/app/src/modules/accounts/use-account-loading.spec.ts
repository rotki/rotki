import type { ComputedRef } from 'vue';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';

const mockAddRunning = ref<boolean>(false);
const mockRemoveRunning = ref<boolean>(false);

vi.mock('@vueuse/core', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@vueuse/core')>();
  return { ...actual, createSharedComposable: <T>(fn: T): T => fn };
});

function activeFor(part?: string): boolean {
  if (part === 'add')
    return get(mockAddRunning);
  if (part === 'remove')
    return get(mockRemoveRunning);
  return false;
}

const useWorkStatus = vi.fn((_kind: string, part?: string, _chain?: string): ComputedRef<WorkStatus> =>
  computed<WorkStatus>(() => {
    const active = activeFor(part);
    return { active, everCompleted: false, pending: false, running: active };
  }));

const useWorkStatusPrefix = vi.fn((_kind: string, part?: string): ComputedRef<WorkStatus> =>
  computed<WorkStatus>(() => {
    const active = activeFor(part);
    return { active, everCompleted: false, pending: false, running: active };
  }));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({ useWorkStatus, useWorkStatusPrefix }),
}));

describe('useAccountLoading', () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(mockAddRunning, false);
    set(mockRemoveRunning, false);
  });

  async function importModule(): Promise<typeof import('./use-account-loading')> {
    return import('./use-account-loading');
  }

  it('should not be loading when nothing is running', async () => {
    const { useAccountLoading } = await importModule();
    const { loading } = useAccountLoading();
    expect(get(loading)).toBe(false);
  });

  it('should be loading while an add-account task runs', async () => {
    const { useAccountLoading } = await importModule();
    const { isAccountOperationRunning, loading } = useAccountLoading();
    set(mockAddRunning, true);
    expect(get(loading)).toBe(true);
    expect(get(isAccountOperationRunning())).toBe(true);
  });

  it('should be loading while a remove-account task runs', async () => {
    const { useAccountLoading } = await importModule();
    const { loading } = useAccountLoading();
    set(mockRemoveRunning, true);
    expect(get(loading)).toBe(true);
  });

  it('should be loading while the pending flag is set', async () => {
    const { useAccountLoading } = await importModule();
    const { loading, pending } = useAccountLoading();
    set(pending, true);
    expect(get(loading)).toBe(true);
  });

  it('should be loading while balances are refreshing', async () => {
    const { useAccountLoading } = await importModule();
    const { loading } = useAccountLoading();
    useBalanceRefreshState().start('eth');
    expect(get(loading)).toBe(true);
  });

  // Add ids end in the address, so the per-chain gate has to match by prefix or it never fires;
  // remove ids are chain-only and stay an exact lookup.
  it('should pass the blockchain filter to the task lookup', async () => {
    const { useAccountLoading } = await importModule();
    const { isAccountOperationRunning } = useAccountLoading();
    isAccountOperationRunning('eth');
    expect(useWorkStatusPrefix).toHaveBeenCalledWith('accounts', 'add', 'eth');
    expect(useWorkStatus).toHaveBeenCalledWith('accounts', 'remove', 'eth');
  });
});
