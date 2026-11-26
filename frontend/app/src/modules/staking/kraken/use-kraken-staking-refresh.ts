import { watchImmediate } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { type MaybeRefOrGetter, toValue } from 'vue';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { refDebounced } from '@/modules/core/common/async/scoped-timers';
import { useKrakenStakingOperations } from '@/modules/staking/kraken/use-kraken-staking-operations';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';

interface UseKrakenStakingRefreshOptions {
  /** Whether a Kraken exchange is connected; the events are queried only while it is. */
  connected: MaybeRefOrGetter<boolean>;
  /** Reloads the history events section after a full page refresh. */
  reloadEvents: () => void;
}

interface UseKrakenStakingRefreshReturn {
  refresh: (ignoreCache?: boolean) => Promise<void>;
  refreshPage: () => Promise<void>;
}

export function useKrakenStakingRefresh(options: UseKrakenStakingRefreshOptions): UseKrakenStakingRefreshReturn {
  const { connected, reloadEvents } = options;
  const { dateFilterKey, events } = storeToRefs(useKrakenStakingStore());
  const { fetchEvents: load } = useKrakenStakingOperations();
  const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();
  const { refreshPrices } = usePriceRefresh();

  async function refresh(ignoreCache: boolean = false): Promise<void> {
    resetProtocolStatsPriceQueryStatus('kraken');
    await load(ignoreCache);
    const assets = get(events).received.map(item => item.asset);
    await refreshPrices(ignoreCache, assets);
  }

  async function refreshPage(): Promise<void> {
    await refresh(true);
    reloadEvents();
  }

  /**
   * The date pills write a value per picker emit, and a year typed digit by digit emits once per
   * digit (`2` and `20` and `202` are each a valid date). Every write here is a POST to
   * `/staking/kraken` plus a price refresh, so the trigger is debounced and a burst of intermediate
   * dates settles into one query. The key is watched rather than the bounds themselves: it changes
   * only when a bound does, where the object it comes from is rewritten by any pagination change.
   * The debounced ref starts at the current value, so the first run after mount is not delayed.
   */
  const settledDateFilterKey = refDebounced(dateFilterKey, 400);

  watchImmediate([settledDateFilterKey, (): boolean => toValue(connected)], async ([_, isKrakenConnected]) => {
    if (isKrakenConnected) {
      await refresh();
    }
  });

  return {
    refresh,
    refreshPage,
  };
}
