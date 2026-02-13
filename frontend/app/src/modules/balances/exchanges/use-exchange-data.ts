import type { ComputedRef, MaybeRef } from 'vue';
import type { AssetProtocolBalances } from '@/types/blockchain/balances';
import type { Exchange, ExchangeInfo } from '@/types/exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { sortDesc } from '@/utils/bignumbers';
import { balanceSum, exchangeAssetSum } from '@/utils/calculation';

interface UseExchangeDataReturn {
  useBaseExchangeBalances: (exchange?: MaybeRef<string>) => ComputedRef<AssetProtocolBalances>;
  exchanges: ComputedRef<ExchangeInfo[]>;
  syncingExchanges: ComputedRef<Exchange[]>;
  isSameExchange: (a: Exchange, b: Exchange) => boolean;
}

export function useExchangeData(): UseExchangeDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { nonSyncingExchanges } = storeToRefs(useGeneralSettingsStore());

  const exchanges = computed<ExchangeInfo[]>(() => {
    const balances = get(exchangeBalances);
    return Object.keys(balances)
      .map(value => ({
        balances: balances[value],
        location: value,
        total: exchangeAssetSum(balances[value]),
      }))
      .sort((a, b) => sortDesc(a.total, b.total));
  });

  const useBaseExchangeBalances = (
    exchange?: MaybeRef<string>,
  ): ComputedRef<AssetProtocolBalances> => computed<AssetProtocolBalances>(() => {
    const balances = get(exchangeBalances);
    const name = exchange ? get(exchange) : undefined;
    const protocolBalances: AssetProtocolBalances = {};

    for (const [exchange, assets] of Object.entries(balances)) {
      if (name && name !== exchange) {
        continue;
      }

      for (const [asset, balance] of Object.entries(assets)) {
        if (!protocolBalances[asset]) {
          protocolBalances[asset] = {};
        }
        if (!protocolBalances[asset][exchange]) {
          protocolBalances[asset][exchange] = balance;
        }
        else {
          protocolBalances[asset][exchange] = balanceSum(protocolBalances[asset][exchange], balance);
        }
      }
    }

    return protocolBalances;
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
    useBaseExchangeBalances,
    syncingExchanges,
    isSameExchange,
  };
}
