import type { Ref } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { TaskType } from '@/modules/core/tasks/task-type';

const h = vi.hoisted(() => ({ useIsTaskRunning: vi.fn() }));

vi.mock('@vueuse/core', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@vueuse/core')>();
  return { ...actual, createSharedComposable: <T>(fn: T): T => fn };
});

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn(() => ({ useIsTaskRunning: h.useIsTaskRunning })),
}));

let addRunning: Ref<boolean>;
let removeRunning: Ref<boolean>;

describe('useAccountLoading', () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    addRunning = ref<boolean>(false);
    removeRunning = ref<boolean>(false);
    h.useIsTaskRunning.mockImplementation((type: TaskType): Ref<boolean> => {
      if (type === TaskType.ADD_ACCOUNT)
        return addRunning;
      if (type === TaskType.REMOVE_ACCOUNT)
        return removeRunning;
      return ref<boolean>(false);
    });
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
    set(addRunning, true);
    expect(get(loading)).toBe(true);
    expect(get(isAccountOperationRunning())).toBe(true);
  });

  it('should be loading while a remove-account task runs', async () => {
    const { useAccountLoading } = await importModule();
    const { loading } = useAccountLoading();
    set(removeRunning, true);
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

  it('should pass the blockchain filter to the task lookup', async () => {
    const { useAccountLoading } = await importModule();
    const { isAccountOperationRunning } = useAccountLoading();
    isAccountOperationRunning('eth');
    expect(h.useIsTaskRunning).toHaveBeenCalledWith(TaskType.ADD_ACCOUNT, { blockchain: 'eth' });
    expect(h.useIsTaskRunning).toHaveBeenCalledWith(TaskType.REMOVE_ACCOUNT, { blockchain: 'eth' });
  });
});
