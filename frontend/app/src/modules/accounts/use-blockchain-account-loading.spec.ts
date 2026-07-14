import type { Ref } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { TaskType } from '@/modules/core/tasks/task-type';

const h = vi.hoisted(() => ({
  getIsLoading: vi.fn((): boolean => false),
  isTaskRunning: vi.fn((): boolean => false),
  useIsTaskRunning: vi.fn(),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn(() => ({ isTaskRunning: h.isTaskRunning, useIsTaskRunning: h.useIsTaskRunning })),
}));

vi.mock('@/modules/core/common/use-status-store', () => ({
  useStatusStore: vi.fn(() => ({ getIsLoading: h.getIsLoading })),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const vue = await import('vue');
  return {
    useSupportedChains: vi.fn(() => ({
      supportedChains: vue.ref([
        { id: 'eth', type: 'evm' },
        { id: 'optimism', type: 'evm' },
      ]),
    })),
  };
});

describe('useBlockchainAccountLoading', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    h.isTaskRunning.mockReturnValue(false);
    h.getIsLoading.mockReturnValue(false);
    h.useIsTaskRunning.mockImplementation((): Ref<boolean> => ref<boolean>(false));
  });

  async function importModule(): Promise<typeof import('./use-blockchain-account-loading')> {
    return import('./use-blockchain-account-loading');
  }

  it('should report every flag as idle when nothing is happening', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.isSectionLoading)).toBe(false);
    expect(get(loading.operationRunning)).toBe(false);
    expect(get(loading.isDetectingTokens)).toBe(false);
    expect(get(loading.refreshDisabled)).toBe(false);
    expect(get(loading.deleteDisabled)).toBe(false);
    expect(get(loading.isLoadingActive)).toBe(false);
  });

  it('should be section loading when the blockchain section loads', async () => {
    h.getIsLoading.mockReturnValue(true);
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.isSectionLoading)).toBe(true);
    expect(get(loading.refreshDisabled)).toBe(true);
    expect(get(loading.isLoadingActive)).toBe(true);
  });

  it('should be section loading when a chain is refreshing', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    useBalanceRefreshState().start('eth');
    expect(get(loading.isSectionLoading)).toBe(true);
  });

  it('should flag a running add/remove operation', async () => {
    h.useIsTaskRunning.mockImplementation((type: TaskType): Ref<boolean> =>
      ref<boolean>(type === TaskType.ADD_ACCOUNT));
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.operationRunning)).toBe(true);
    expect(get(loading.deleteDisabled)).toBe(true);
    expect(get(loading.isLoadingActive)).toBe(true);
  });

  it('should disable delete while balances are fetching', async () => {
    h.isTaskRunning.mockReturnValue(true);
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.deleteDisabled)).toBe(true);
  });

  it('should detect tokens for an evm category when mass detection runs', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading('evm');
    useTokenDetectionStore().setMassDetecting('eth');
    expect(get(loading.isDetectingTokens)).toBe(true);
    expect(get(loading.refreshDisabled)).toBe(true);
  });

  it('should not detect tokens for a non-evm category', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading('bitcoin');
    useTokenDetectionStore().setMassDetecting('eth');
    expect(get(loading.isDetectingTokens)).toBe(false);
  });
});
