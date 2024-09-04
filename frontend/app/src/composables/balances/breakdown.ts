import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { AssetBreakdown } from '@/types/blockchain/accounts';

interface UseBalancesBreakdownReturn {
  assetBreakdown: (asset: string) => ComputedRef<AssetBreakdown[]>;
  locationBreakdown: (identifier: MaybeRef<string>) => ComputedRef<AssetBalanceWithPrice[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
}

export function useBalancesBreakdown(): UseBalancesBreakdownReturn {
  const manualStore = useManualBalancesStore();
  const { manualBalanceByLocation } = storeToRefs(manualStore);
  const { getBreakdown: getManualBreakdown, getLocationBreakdown: getManualLocationBreakdown } = manualStore;
  const {
    getBreakdown: getExchangeBreakdown,
    getLocationBreakdown: getExchangesLocationBreakdown,
    getByLocationBalances: getExchangesByLocationBalances,
  } = useExchangeBalancesStore();
  const { getBreakdown } = useBlockchainStore();
  const { locationBreakdown: blockchainLocationBreakdown, blockchainTotal } = useBlockchainAggregatedBalances();
  const { toSelectedCurrency, assetPrice } = useBalancePricesStore();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();

  const assetBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() =>
    groupAssetBreakdown(
      get(getBreakdown(asset))
        .concat(get(getManualBreakdown(asset)))
        .concat(get(getExchangeBreakdown(asset)))
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
    locationBreakdown,
    balancesByLocation,
  };
}
