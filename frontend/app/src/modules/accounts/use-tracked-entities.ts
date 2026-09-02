import type { ComputedRef, Ref } from 'vue';
import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';

interface UseTrackedEntitiesReturn {
  /** the user has nothing in rotki to have a portfolio or a history from */
  tracksNothing: ComputedRef<boolean>;
  /** the accounts have not been read yet, so {@link tracksNothing} is not an answer */
  loading: Readonly<Ref<boolean>>;
}

/**
 * Whether the user tracks anything at all.
 *
 * Every source here can only ever *add* evidence that something is tracked, so the
 * answer is only trustworthy once the accounts have been read - before that an empty
 * store is indistinguishable from an empty portfolio. That is what `loading` is for.
 *
 * Validators are not special-cased: they are accounts under `eth2` like any other chain.
 */
export function useTrackedEntities(): UseTrackedEntitiesReturn {
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { ready } = useAccountLoadState();

  const tracksNothing = computed<boolean>(() =>
    Object.values(get(accounts)).every(chainAccounts => chainAccounts.length === 0)
    && get(connectedExchanges).length === 0
    && get(manualBalances).length === 0
    && get(manualLiabilities).length === 0,
  );

  const loading = logicNot(ready);

  return {
    loading,
    tracksNothing,
  };
}
