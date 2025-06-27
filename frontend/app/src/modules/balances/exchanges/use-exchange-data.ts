import type { AssetProtocolBalances } from '@/types/blockchain/balances';
import type { ExchangeInfo } from '@/types/exchanges';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/utils/bignumbers';
import { balanceSum, exchangeAssetSum } from '@/utils/calculation';

interface UseExchangeDataReturn {
  useBaseExchangeBalances: (exchange?: MaybeRef<string>) => ComputedRef<AssetProtocolBalances>;
  exchanges: ComputedRef<ExchangeInfo[]>;
}

export function useExchangeData(): UseExchangeDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());

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

  return {
    exchanges,
    useBaseExchangeBalances,
  };
}
