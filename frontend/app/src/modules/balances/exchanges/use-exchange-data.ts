import type { ComputedRef } from 'vue';
import type { Exchange, ExchangeInfo } from '@/modules/balances/types/exchanges';
import type { ConnectionRef } from '@/modules/core/common/connection';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';
import { useSetting } from '@/modules/settings/use-setting';

interface UseExchangeDataReturn {
  exchanges: ComputedRef<ExchangeInfo[]>;
  syncingExchanges: ComputedRef<Exchange[]>;
  isSameExchange: (a: ConnectionRef, b: ConnectionRef) => boolean;
}

export function useExchangeData(): UseExchangeDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const nonSyncingExchanges = useSetting('nonSyncingExchanges');
  const { isAssetIgnored } = useAssetsStore();

  const exchanges = computed<ExchangeInfo[]>(() => {
    const balances = get(exchangeBalances);
    return Object.keys(balances)
      .map(value => ({
        balances: balances[value],
        location: value,
        total: exchangeAssetSum(balances[value], isAssetIgnored),
      }))
      .sort((a, b) => sortDesc(a.total, b.total));
  });

  /** Connections are the same when their identifiers are, whatever they are named now. */
  function isSameExchange(a: ConnectionRef, b: ConnectionRef): boolean {
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
