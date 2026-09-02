import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseAccountLoadingStates<T extends BlockchainAccountBalance> {
  accountOperation: ComputedRef<boolean>;
  isInitialLoading: ComputedRef<boolean>;
  isRowLoading: (row: AccountDataRow<T>) => boolean;
  isSectionLoading: ComputedRef<boolean>;
}

export function useAccountLoadingStates<T extends BlockchainAccountBalance>(
  category: MaybeRefOrGetter<string>,
): UseAccountLoadingStates<T> {
  const { useIsActivePrefix } = useTaskCenter();
  const { statusOf, statusOfPrefix, version } = useTaskOrchestrator();
  const refreshState = useBalanceRefreshState();
  const { hydratingChains, refreshingChains } = storeToRefs(refreshState);
  const { isSectionLoading } = useBlockchainAccountLoading(category);
  const { chainIds } = useAccountCategoryHelper(category);

  const accountOperation = logicOr(
    useIsActivePrefix(ActivityKind.ACCOUNTS, ActivityPart.ADD),
    useIsActivePrefix(ActivityKind.ACCOUNTS, ActivityPart.REMOVE),
    isSectionLoading,
  );

  /**
   * Whether the table has nothing to show *yet*, as opposed to nothing to show.
   *
   * @remarks
   * "Active" spans both layers: hydration is not an activity, so the orchestrator alone reports a
   * chain being read from the DB as idle. A category whose chain list has not resolved falls back
   * to every chain.
   */
  const isInitialLoading = computed<boolean>(() => {
    get(version); // touch the change counter so this re-reads the non-reactive ledger
    const hydrating = get(hydratingChains);
    const chains = get(chainIds);
    if (chains.length === 0) {
      const { active, everCompleted } = statusOf(ActivityKind.BLOCKCHAIN_BALANCES);
      return (active || hydrating.size > 0) && !everCompleted;
    }
    return chains.some((chain) => {
      const { active, everCompleted } = statusOfPrefix(ActivityKind.BLOCKCHAIN_BALANCES, chain);
      return (active || hydrating.has(chain)) && !everCompleted;
    });
  });

  function isRowLoading(row: AccountDataRow<T>): boolean {
    const refreshing = get(refreshingChains);
    if (row.type === 'account')
      return refreshing.has(row.chain);
    else
      return row.chains.some(chain => refreshing.has(chain));
  }

  return {
    accountOperation,
    isInitialLoading,
    isRowLoading,
    isSectionLoading,
  };
}
