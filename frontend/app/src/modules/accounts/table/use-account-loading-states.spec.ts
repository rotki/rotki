import type { ComputedRef } from 'vue';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useAccountLoadingStates } from './use-account-loading-states';

interface OrchestratorStatus { active: boolean; everCompleted: boolean }

const state = vi.hoisted((): { chainIds: string[]; everCompleted: boolean } => ({
  chainIds: ['eth'],
  everCompleted: false,
}));

vi.mock('@/modules/accounts/use-account-category-helper', () => ({
  useAccountCategoryHelper: vi.fn(() => ({ chainIds: computed(() => state.chainIds) })),
}));

vi.mock('@/modules/accounts/use-blockchain-account-loading', () => ({
  useBlockchainAccountLoading: vi.fn(() => ({ isSectionLoading: computed(() => false) })),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: vi.fn(() => ({ useIsActivePrefix: (): ComputedRef<boolean> => computed<boolean>(() => false) })),
}));

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn(() => ({
    statusOf: (): OrchestratorStatus => ({ active: false, everCompleted: state.everCompleted }),
    statusOfPrefix: (): OrchestratorStatus => ({ active: false, everCompleted: state.everCompleted }),
    version: computed<number>(() => 0),
  })),
}));

describe('useAccountLoadingStates', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    state.chainIds = ['eth'];
    state.everCompleted = false;
  });

  it('should report initial loading while a chain is only hydrating', () => {
    const { startHydration } = useBalanceRefreshState();
    const { isInitialLoading } = useAccountLoadingStates<BlockchainAccountBalance>('evm');

    expect(get(isInitialLoading)).toBe(false);

    startHydration('eth');

    expect(get(isInitialLoading)).toBe(true);
  });

  it('should stop reporting initial loading once the chain has completed', () => {
    const { startHydration } = useBalanceRefreshState();
    state.everCompleted = true;
    const { isInitialLoading } = useAccountLoadingStates<BlockchainAccountBalance>('evm');

    startHydration('eth');

    expect(get(isInitialLoading)).toBe(false);
  });
});
