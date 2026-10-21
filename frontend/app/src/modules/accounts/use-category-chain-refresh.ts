import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';

export interface ChainRefreshState {
  chain: string;
  name: string;
  /** Seconds since the epoch of the last balance query, `undefined` while the chain was never queried. */
  timestamp: number | undefined;
  /** The `disabledChainQueries` setting excludes the whole chain, or every account tracked on it. */
  skipped: boolean;
}

interface UseCategoryChainRefreshReturn {
  chains: ComputedRef<ChainRefreshState[]>;
  refreshable: ComputedRef<ChainRefreshState[]>;
  oldest: ComputedRef<ChainRefreshState | undefined>;
}

/**
 * Orders chains from the stalest to the freshest: a chain never queried comes first, a skipped
 * chain last, since its age says nothing about the balances the user can refresh.
 */
function byStaleness(a: ChainRefreshState, b: ChainRefreshState): number {
  if (a.skipped !== b.skipped)
    return a.skipped ? 1 : -1;

  return (a.timestamp ?? -1) - (b.timestamp ?? -1);
}

/**
 * The last balance refresh of each chain in an account category that holds tracked accounts.
 *
 * @remarks
 * The backend keeps one refresh timestamp per chain, and a refresh of some addresses bumps it too,
 * so the age is a chain's, never an account's. Chains without accounts are left out: their
 * timestamp is either missing or says nothing about anything on the page.
 *
 * @returns `chains` stalest first, `refreshable` without the skipped chains, and `oldest`, the
 * first refreshable chain.
 */
export function useCategoryChainRefresh(category: MaybeRefOrGetter<string>): UseCategoryChainRefreshReturn {
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { refreshTimestamps } = storeToRefs(useBlockchainRefreshTimestampsStore());
  const { chainIds } = useAccountCategoryHelper(category);
  const { getChainName } = useSupportedChains();
  const { isAddressExcluded } = useDisabledChains();

  const chains = computed<ChainRefreshState[]>(() => {
    const tracked = get(accounts);
    const timestamps = get(refreshTimestamps);

    return get(chainIds)
      .filter(chain => (tracked[chain]?.length ?? 0) > 0)
      .map(chain => ({
        chain,
        name: getChainName(chain),
        skipped: tracked[chain].every(account => isAddressExcluded(chain, getAccountAddress(account))),
        timestamp: timestamps[chain],
      }))
      .sort(byStaleness);
  });

  const refreshable = computed<ChainRefreshState[]>(() => get(chains).filter(state => !state.skipped));

  const oldest = computed<ChainRefreshState | undefined>(() => get(refreshable)[0]);

  return {
    chains,
    oldest,
    refreshable,
  };
}
