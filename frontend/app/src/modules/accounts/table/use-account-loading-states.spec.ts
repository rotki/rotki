import type { ComputedRef } from 'vue';
import type { AccountDataRow } from './types';
import type { AddressGroupWithBalance, BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getGroupId } from '@/modules/accounts/account-utils';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useAccountLoadingStates } from './use-account-loading-states';

interface OrchestratorStatus { active: boolean; everCompleted: boolean }

const state = vi.hoisted((): { chainIds: string[]; everCompleted: boolean; prefixReads: unknown[][]; kindReads: unknown[][] } => ({
  chainIds: ['eth'],
  everCompleted: false,
  kindReads: [],
  prefixReads: [],
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
    statusOf: (...args: unknown[]): OrchestratorStatus => {
      state.kindReads.push(args);
      return { active: false, everCompleted: state.everCompleted };
    },
    statusOfPrefix: (...args: unknown[]): OrchestratorStatus => {
      state.prefixReads.push(args);
      return { active: false, everCompleted: state.everCompleted };
    },
    version: computed<number>(() => 0),
  })),
}));

describe('useAccountLoadingStates', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    state.chainIds = ['eth'];
    state.everCompleted = false;
    state.kindReads = [];
    state.prefixReads = [];
  });

  it('should read each chain by the chain balance prefix its refresh jobs sit under', () => {
    const { isInitialLoading } = useAccountLoadingStates<BlockchainAccountBalance>('evm');

    get(isInitialLoading);

    expect(state.prefixReads).toStrictEqual([['blockchain-balances', 'eth']]);
    expect(state.kindReads).toStrictEqual([]);
  });

  it('should fall back to every chain while the category\'s chain list has not resolved', () => {
    state.chainIds = [];
    const { startHydration } = useBalanceRefreshState();
    const { isInitialLoading } = useAccountLoadingStates<BlockchainAccountBalance>('evm');

    startHydration('optimism');

    expect(get(isInitialLoading)).toBe(true);
    expect(state.kindReads.at(-1)).toStrictEqual(['blockchain-balances']);
    expect(state.prefixReads).toStrictEqual([]);
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

  it('should find a known balance on one chain while another is pending', () => {
    const row: AccountDataRow<AddressGroupWithBalance> = {
      address: '0xabc',
      category: 'evm',
      chains: ['eth', 'optimism'],
      id: getGroupId({ address: '0xabc', chains: ['eth', 'optimism'], kind: 'address' }),
      kind: 'address',
      type: 'group',
      value: bigNumberify(12),
    };
    const refresh = useBalanceRefreshState();
    const { hasRowBalance, isRowPending } = useAccountLoadingStates<AddressGroupWithBalance>('evm');

    refresh.markPending('optimism', row.address, 1);
    expect(isRowPending(row)).toBe(true);
    expect(hasRowBalance(row)).toBe(false);

    useBalancesStore().updateBalances('eth', {
      perAccount: { eth: { [row.address]: { assets: {}, liabilities: {} } } },
      totals: { assets: {}, liabilities: {} },
    });
    expect(hasRowBalance(row)).toBe(true);
    expect(isRowPending(row)).toBe(true);
  });

  it('should stop marking an available value as pending when only excluded chains remain', () => {
    const row: AccountDataRow<AddressGroupWithBalance> = {
      address: '0xabc',
      category: 'evm',
      chains: ['eth', 'optimism'],
      id: getGroupId({ address: '0xabc', chains: ['eth', 'optimism'], kind: 'address' }),
      kind: 'address',
      type: 'group',
      value: bigNumberify(12),
    };
    const refresh = useBalanceRefreshState();
    const settings = useSettingsRepo();
    const { isRowPending } = useAccountLoadingStates<AddressGroupWithBalance>('evm');
    refresh.markPending('optimism', row.address, 1);
    useBalancesStore().updateBalances('eth', {
      perAccount: { eth: { [row.address]: { assets: {}, liabilities: {} } } },
      totals: { assets: {}, liabilities: {} },
    });

    expect(isRowPending(row)).toBe(true);
    settings.updateGeneral({ ...settings.general, disabledChainQueries: { optimism: [] } });
    expect(isRowPending(row)).toBe(false);
    settings.updateGeneral({ ...settings.general, disabledChainQueries: { optimism: ['0xABC'] } });
    expect(isRowPending(row)).toBe(false);
    settings.updateGeneral({ ...settings.general, disabledChainQueries: {} });
    expect(isRowPending(row)).toBe(true);
  });

  it('should keep an entirely unqueried excluded account pending instead of showing zero', () => {
    const row: AccountDataRow<AddressGroupWithBalance> = {
      address: '0xabc',
      category: 'evm',
      chains: ['optimism'],
      id: getGroupId({ address: '0xabc', chains: ['optimism'], kind: 'address' }),
      kind: 'address',
      type: 'group',
      value: bigNumberify(0),
    };
    const settings = useSettingsRepo();
    settings.updateGeneral({ ...settings.general, disabledChainQueries: { optimism: ['0xABC'] } });
    useBalanceRefreshState().markPending('optimism', row.address, 1);

    expect(useAccountLoadingStates<AddressGroupWithBalance>('evm').isRowPending(row)).toBe(true);
  });
});
