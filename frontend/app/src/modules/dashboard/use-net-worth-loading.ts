import type { ComputedRef } from 'vue';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';

/**
 * Whether the dashboard header has nothing to put in the net worth yet.
 *
 * The net worth is a sum, so it is zero until balances land and then climbs as each chain arrives.
 * Neither end of that is worth showing: a large "0.00" reads as a real balance, and a total that
 * ratchets from a fraction of itself is wrong for as long as it moves, with nothing on screen
 * saying so. The header therefore waits for the whole first load, not for the first value.
 *
 * It has to be a latch rather than a live loading read, for two reasons. The balance activities
 * are submitted after the dashboard has rendered, so a live read is false on the first frames and
 * the header would flicker value, skeleton, value. And once the first load has settled the number
 * stays: a later refresh must not blank the total the user is reading.
 *
 * So: closed until a load settles with the ledger holding a completed chain, then open for good.
 */
export function useNetWorthLoading(): ComputedRef<boolean> {
  const { loadingBlockchainBalances } = useBalancesLoading();
  const { hasCachedData } = useBalanceStatus();

  const loaded = shallowRef<boolean>(false);

  watch([loadingBlockchainBalances, hasCachedData], ([loading, cached]) => {
    if (get(loaded))
      return;

    if (cached && !loading)
      set(loaded, true);
  }, { immediate: true });

  return computed<boolean>(() => !get(loaded));
}
