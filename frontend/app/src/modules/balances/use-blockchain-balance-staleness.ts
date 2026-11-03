import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';
import { toChainKey } from '@/modules/core/common/chains';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';

interface UseBlockchainBalanceStalenessReturn {
  lastRefreshed: Ref<string>;
  lastRefreshTimestamp: ComputedRef<number | undefined>;
}

/**
 * Returns a reactive "time ago" string for the oldest blockchain balance refresh.
 * If a chain is provided, returns the timestamp for that specific chain.
 * If no chain is provided, returns the oldest timestamp across all chains that are still refreshed.
 * A chain with every query disabled is never refreshed, and the store only merges timestamps, so its old entry
 * would otherwise keep being reported after the setting is saved.
 */
export function useBlockchainBalanceStaleness(chain?: MaybeRefOrGetter<string | undefined>): UseBlockchainBalanceStalenessReturn {
  const { refreshTimestamps } = storeToRefs(useBlockchainRefreshTimestampsStore());
  const { isAddressExcluded, isChainExcluded } = useDisabledChains();
  const { getAccounts } = useBlockchainAccountsStore();

  /**
   * A chain is not refreshed when it is disabled as a whole, or when it tracks accounts and every
   * one of them is excluded by an address rule. The timestamp keys went through the camelCase
   * response transformer (`polygonPos`) while the accounts store is keyed by the raw chain id
   * (`polygon_pos`), so the key is normalized before the lookup.
   */
  const isNotRefreshed = (key: string): boolean => {
    if (isChainExcluded(key))
      return true;

    // xpub group headers are synthetic rows over their derived addresses, not tracked addresses
    const accounts = getAccounts(toChainKey(key)).filter(account => !account.groupHeader);
    return accounts.length > 0 && accounts.every(account => isAddressExcluded(key, getAccountAddress(account)));
  };

  const lastRefreshTimestamp = computed<number | undefined>(() => {
    const timestamps = get(refreshTimestamps);
    const chainValue = toValue(chain);

    if (chainValue)
      return timestamps[chainValue];

    const values = Object.entries(timestamps)
      .filter(([key]) => !isNotRefreshed(key))
      .map(([, timestamp]) => timestamp);
    if (values.length === 0)
      return undefined;

    return Math.min(...values);
  });

  const timestampMs = computed<number>(() => {
    const ts = get(lastRefreshTimestamp);
    return ts ? ts * 1000 : 0;
  });

  const lastRefreshed = useTimeAgo(timestampMs);

  return {
    lastRefreshed,
    lastRefreshTimestamp,
  };
}
