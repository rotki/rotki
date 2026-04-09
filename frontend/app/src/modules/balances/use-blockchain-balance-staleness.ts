import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';

interface UseBlockchainBalanceStalenessReturn {
  lastRefreshed: Ref<string>;
  lastRefreshTimestamp: ComputedRef<number | undefined>;
}

/**
 * Returns a reactive "time ago" string for the oldest blockchain balance refresh.
 * If a chain is provided, returns the timestamp for that specific chain.
 * If no chain is provided, returns the oldest timestamp across all chains.
 */
export function useBlockchainBalanceStaleness(chain?: MaybeRefOrGetter<string | undefined>): UseBlockchainBalanceStalenessReturn {
  const { refreshTimestamps } = storeToRefs(useBlockchainRefreshTimestampsStore());

  const lastRefreshTimestamp = computed<number | undefined>(() => {
    const timestamps = get(refreshTimestamps);
    const chainValue = toValue(chain);

    if (chainValue)
      return timestamps[chainValue];

    const values = Object.values(timestamps);
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
