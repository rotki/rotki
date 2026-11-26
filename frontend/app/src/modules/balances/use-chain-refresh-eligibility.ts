import { get } from '@vueuse/shared';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';

interface UseChainRefreshEligibilityReturn {
  /** Whether `disabledChainQueries` skips this one address of `chain`. */
  isAddressExcluded: (chain: string, address: string) => boolean;
  /** Whether `disabledChainQueries` skips `chain` as a whole. */
  isChainExcluded: (chain: string) => boolean;
  isChainRefreshing: (chain: string) => boolean;
  isEveryAccountExcluded: (chain: string) => boolean;
}

/**
 * The checks a chain's network refresh makes before querying: whether the user's
 * `disabledChainQueries` leaves anything to ask for, and whether a refresh of it is already running.
 */
export function useChainRefreshEligibility(): UseChainRefreshEligibilityReturn {
  const refreshState = useBalanceRefreshState();
  const { isAddressExcluded, isChainExcluded, isEveryAddressExcluded } = useDisabledChains();
  const { getAccounts } = useBlockchainAccountsStore();

  /**
   * Whether every account tracked on `chain` is skipped one by one, so a query of the whole chain
   * would ask the backend for nothing.
   *
   * @remarks
   * The backend already leaves skipped addresses out of a whole-chain query; answering here spares
   * the task round trip and settles the chain as skipped rather than refreshed. A chain without
   * accounts is not this case: it is skipped later, for having no accounts, and its balances are
   * cleared. These keep theirs.
   */
  const isEveryAccountExcluded = (chain: string): boolean =>
    isEveryAddressExcluded(chain, getAccounts(chain).map(getAccountAddress));

  /**
   * Whether a *network* refresh is already running for this chain.
   *
   * It does not wait on the chain's hydration from the DB, and must not: the two layers overlap
   * by design. A cached read landing after a network result would overwrite fresh balances with
   * stale ones, which balance writes being monotonic prevents outright: the older payload is
   * discarded whichever order the two land in. Two mechanisms for one hazard, and the cheaper one
   * wins.
   *
   * Read by the `periodic` branch only, at submit and again at start. It is not redundant with
   * `submitTask`'s id dedup: dedup covers a run that is *submitted*, this covers the window where
   * the POST itself is in flight. The submit check is what keeps a tick from querying right after
   * `oneBalanceQueryPerChain` released it, when the chain it was waiting on has just refreshed.
   */
  const isChainRefreshing = (chain: string): boolean => get(refreshState.refreshingChains).has(chain);

  return {
    isAddressExcluded,
    isChainExcluded,
    isChainRefreshing,
    isEveryAccountExcluded,
  };
}
