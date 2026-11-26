import type { BlockchainAccountGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { startPromise } from '@shared/utils';
import { watchImmediate } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { watchDebounced } from '@/modules/core/common/async/scoped-timers';

interface UseAccountBalancesFetchTriggersOptions {
  /** The account category the page lists. */
  readonly category: MaybeRefOrGetter<string>;
  /** The page of accounts the table renders. */
  readonly accounts: MaybeRefOrGetter<Collection<BlockchainAccountGroupWithBalance>>;
  /** Whether a page fetch is in flight. */
  readonly isFetching: MaybeRefOrGetter<boolean>;
  /** The chains of the category. */
  readonly chainIds: MaybeRefOrGetter<string[]>;
  /** Fetches the current page again. */
  readonly fetchData: () => Promise<void>;
}

interface UseAccountBalancesFetchTriggersReturn {
  /** Whether an empty page is not the answer yet, so the table shows loading rather than "no accounts". */
  readonly awaitingAccounts: ComputedRef<boolean>;
}

/**
 * Keeps the account balances page current: fetches it right away, again whenever the accounts or
 * the balances change, and once a balance read for the category settles.
 */
export function useAccountBalancesFetchTriggers(
  options: UseAccountBalancesFetchTriggersOptions,
): UseAccountBalancesFetchTriggersReturn {
  const { accounts, category, chainIds, fetchData, isFetching } = options;

  const { visibleBalances: balances } = storeToRefs(useBalancesStore());
  const accountsStore = useBlockchainAccountsStore();
  const { accounts: accountsState } = storeToRefs(accountsStore);
  const { isChainSettled } = accountsStore;

  const { isLoadingActive } = useBlockchainAccountLoading(category);

  /**
   * Whether an empty page is not the answer yet, so the table shows loading rather than "no accounts".
   *
   * @remarks
   * Until a chain of the category has settled (its accounts read loaded or failed), nothing is known,
   * and the page fetch that runs before the accounts land comes back empty. A failed read settles
   * the chain too, so the table then shows the empty state or the fetch error instead of spinning.
   */
  const awaitingAccounts = computed<boolean>(() => {
    if (toValue(accounts).data.length > 0)
      return false;
    // with no chains known for the category there is nothing to wait on
    const categoryChains = toValue(chainIds);
    return toValue(isFetching) || (categoryChains.length > 0 && !categoryChains.some(chain => isChainSettled(chain)));
  });

  watchDebounced(isLoadingActive, async (isLoading, wasLoading) => {
    if (!isLoading && wasLoading)
      await fetchData();
  }, { debounce: 800 });

  watchImmediate([accountsState, balances], () => {
    startPromise(fetchData());
  });

  return {
    awaitingAccounts,
  };
}
