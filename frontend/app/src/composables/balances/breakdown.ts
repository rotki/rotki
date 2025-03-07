import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useBlockchainAggregatedBalances } from '@/composables/blockchain/balances/aggregated';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useBlockchainStore } from '@/store/blockchain';
import { groupAssetBreakdown, mergeAssetBalances } from '@/utils/balances';

interface UseBalancesBreakdownReturn {
  assetBreakdown: (asset: string) => ComputedRef<AssetBreakdown[]>;
  liabilityBreakdown: (asset: string) => ComputedRef<AssetBreakdown[]>;
  locationBreakdown: (identifier: MaybeRef<string>) => ComputedRef<AssetBalanceWithPrice[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
}

export function useBalancesBreakdown(): UseBalancesBreakdownReturn {
  const manualStore = useManualBalancesStore();
  const { manualBalanceByLocation } = storeToRefs(manualStore);
  const { assetBreakdown: manualAssetBreakdown, getLocationBreakdown: getManualLocationBreakdown, liabilityBreakdown: manualLiabilityBreakdown } = manualStore;
  const {
    getBreakdown: getExchangeBreakdown,
    getByLocationBalances: getExchangesByLocationBalances,
    getLocationBreakdown: getExchangesLocationBreakdown,
  } = useExchangeBalancesStore();
  const { assetBreakdown: blockchainAssetBreakdown, liabilityBreakdown: blockchainLiabilityBreakdown } = useBlockchainStore();
  const { blockchainTotal, locationBreakdown: blockchainLocationBreakdown } = useBlockchainAggregatedBalances();
  const { assetPrice, toSelectedCurrency } = useBalancePricesStore();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();

  const assetBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() =>
    groupAssetBreakdown(
      get(blockchainAssetBreakdown(asset))
        .concat(get(manualAssetBreakdown(asset)))
        .concat(get(getExchangeBreakdown(asset)))
        .filter(item => !!item.amount && !item.amount.isZero()),
    ),
  );

  const liabilityBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() =>
    groupAssetBreakdown(
      get(blockchainLiabilityBreakdown(asset))
        .concat(get(manualLiabilityBreakdown(asset)))
        .filter(item => !!item.amount && !item.amount.isZero()),
    ),
  );

  const locationBreakdown = (identifier: MaybeRef<string>): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const id = get(identifier);
      let balances = mergeAssetBalances(get(getManualLocationBreakdown(id)), get(getExchangesLocationBreakdown(id)));

      if (id === TRADE_LOCATION_BLOCKCHAIN)
        balances = mergeAssetBalances(balances, get(blockchainLocationBreakdown));

      return toSortedAssetBalanceWithPrice(balances, asset => get(isAssetIgnored(asset)), assetPrice, true);
    });

  const balancesByLocation = computed<Record<string, BigNumber>>(() => {
    const map: Record<string, BigNumber> = {
      [TRADE_LOCATION_BLOCKCHAIN]: get(toSelectedCurrency(blockchainTotal)),
    };

    const exchange = get(getExchangesByLocationBalances(toSelectedCurrency));
    for (const location in exchange) {
      const total = map[location];
      const usdValue = exchange[location];
      map[location] = total ? total.plus(usdValue) : usdValue;
    }

    const manual = get(manualBalanceByLocation);
    for (const { location, usdValue } of manual) {
      const total = map[location];
      map[location] = total ? total.plus(usdValue) : usdValue;
    }

    return map;
  });

  return {
    assetBreakdown,
    balancesByLocation,
    liabilityBreakdown,
    locationBreakdown,
  };
}
