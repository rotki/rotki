import type { AssetProtocolBalances } from '@/types/blockchain/balances';
import type { ExchangeInfo } from '@/types/exchanges';
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { mergeAssociatedAssets } from '@/utils/balances';
import { sortDesc } from '@/utils/bignumbers';
import { balanceSum, exchangeAssetSum } from '@/utils/calculation';

interface UseExchangeDataReturn {
  balances: ComputedRef<AssetProtocolBalances>;
  getBalances: (exchange: string, hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPrice[]>;
  exchanges: ComputedRef<ExchangeInfo[]>;
}

export function useExchangeData(): UseExchangeDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { useIsAssetIgnored } = useIgnoredAssetsStore();
  const { assetPrice } = usePriceUtils();
  const { assetAssociationMap, getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();

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

  const balances = computed<AssetProtocolBalances>(() => {
    const balances = get(exchangeBalances);
    const association = get(assetAssociationMap);
    const protocolBalances: AssetProtocolBalances = {};

    for (const [exchange, assets] of Object.entries(balances)) {
      for (const [asset, balance] of Object.entries(assets)) {
        const identifier = association[asset] ?? asset;
        if (!protocolBalances[identifier]) {
          protocolBalances[identifier] = {};
        }
        if (!protocolBalances[identifier][exchange]) {
          protocolBalances[identifier][exchange] = balance;
        }
        else {
          protocolBalances[identifier][exchange] = balanceSum(protocolBalances[asset][exchange], balance);
        }
      }
    }

    return protocolBalances;
  });

  const getBalances = (
    exchange: string,
    hideIgnored = true,
  ): ComputedRef<AssetBalanceWithPrice[]> => computed<AssetBalanceWithPrice[]>(() => {
    const balances = get(exchangeBalances);

    if (balances && balances[exchange]) {
      return toSortedAssetBalanceWithPrice(
        get(mergeAssociatedAssets(balances[exchange], getAssociatedAssetIdentifier)),
        asset => hideIgnored && get(useIsAssetIgnored(asset)),
        assetPrice,
      );
    }

    return [];
  });

  return {
    balances,
    exchanges,
    getBalances,
  };
}
