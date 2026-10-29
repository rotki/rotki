import type { ComputedRef } from 'vue';
import type { Exchange, ExchangeInfo } from '@/modules/balances/types/exchanges';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';
import { useSetting } from '@/modules/settings/use-setting';

interface UseExchangeDataReturn {
  exchanges: ComputedRef<ExchangeInfo[]>;
  syncingExchanges: ComputedRef<Exchange[]>;
  isSameExchange: (a: { identifier: string }, b: { identifier: string }) => boolean;
}

export function useExchangeData(): UseExchangeDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const nonSyncingExchanges = useSetting('nonSyncingExchanges');
  const { isAssetIgnored } = useAssetsStore();
  const { bankLocations } = storeToRefs(useBankConnectionsStore());

  /** Bank balances share the map but are not exchanges; they get their own card and page. */
  const exchanges = computed<ExchangeInfo[]>(() => {
    const balances = get(exchangeBalances);
    return Object.keys(balances)
      .filter(location => !get(bankLocations).includes(location))
      .map(value => ({
        balances: balances[value],
        location: value,
        total: exchangeAssetSum(balances[value], isAssetIgnored),
      }))
      .sort((a, b) => sortDesc(a.total, b.total));
  });

  /** Connections are the same when their identifiers are, whatever they are named now. */
  function isSameExchange(a: { identifier: string }, b: { identifier: string }): boolean {
    return a.identifier === b.identifier;
  }

  const syncingExchanges = computed<Exchange[]>(() => get(connectedExchanges).filter(
    exchange => !get(nonSyncingExchanges).includes(exchange.identifier),
  ));

  return {
    exchanges,
    syncingExchanges,
    isSameExchange,
  };
}
