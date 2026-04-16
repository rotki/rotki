import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AssetProtocolBalances } from '@/modules/balances/types/blockchain-balances';
import type { Exchange, ExchangeInfo } from '@/modules/balances/types/exchanges';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/modules/common/data/bignumbers';
import { balanceSum, exchangeAssetSum } from '@/modules/common/data/calculation';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';

interface UseExchangeDataReturn {
  getBaseExchangeBalances: (exchange?: string) => AssetProtocolBalances;
  useBaseExchangeBalances: (exchange?: MaybeRefOrGetter<string>) => ComputedRef<AssetProtocolBalances>;
  exchanges: ComputedRef<ExchangeInfo[]>;
  syncingExchanges: ComputedRef<Exchange[]>;
  isSameExchange: (a: Exchange, b: Exchange) => boolean;
}

export function useExchangeData(): UseExchangeDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { nonSyncingExchanges } = storeToRefs(useGeneralSettingsStore());
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

  function getBaseExchangeBalances(name?: string): AssetProtocolBalances {
    const balances = get(exchangeBalances);
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
  }

  const useBaseExchangeBalances = (
    exchange?: MaybeRefOrGetter<string>,
  ): ComputedRef<AssetProtocolBalances> => computed<AssetProtocolBalances>(() =>
    getBaseExchangeBalances(exchange ? toValue(exchange) : undefined),
  );

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
    getBaseExchangeBalances,
    useBaseExchangeBalances,
    syncingExchanges,
    isSameExchange,
  };
}
