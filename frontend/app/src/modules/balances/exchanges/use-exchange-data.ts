import type { ComputedRef } from 'vue';
import type { Exchange, ExchangeInfo } from '@/modules/balances/types/exchanges';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useSetting } from '@/modules/settings/use-setting';

interface UseExchangeDataReturn {
  exchanges: ComputedRef<ExchangeInfo[]>;
  syncingExchanges: ComputedRef<Exchange[]>;
  isSameExchange: (a: Exchange, b: Exchange) => boolean;
}

export function useExchangeData(): UseExchangeDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const nonSyncingExchanges = useSetting('nonSyncingExchanges');
  const { isAssetIgnored } = useAssetsStore();
  const { banks } = storeToRefs(useLocationStore());

  /** Bank balances share the map but are not exchanges; they get their own card and page. */
  const exchanges = computed<ExchangeInfo[]>(() => {
    const balances = get(exchangeBalances);
    return Object.keys(balances)
      .filter(location => !get(banks).includes(location))
      .map(value => ({
        balances: balances[value],
        location: value,
        total: exchangeAssetSum(balances[value], isAssetIgnored),
      }))
      .sort((a, b) => sortDesc(a.total, b.total));
  });

  function isSameExchange(a: Exchange, b: Exchange): boolean {
    return a.location === b.location && a.name === b.name;
  }

  const syncingExchanges = computed<Exchange[]>(() => get(connectedExchanges).filter(
    exchange => !get(nonSyncingExchanges).some(
      excluded => isSameExchange(excluded, exchange),
    ),
  ));

  return {
    exchanges,
    syncingExchanges,
    isSameExchange,
  };
}
