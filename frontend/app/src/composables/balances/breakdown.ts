import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import type { BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { ComputedRef } from 'vue';
import type { AssetBalanceWithBreakdown } from '@/types/balances';

interface UseBalancesBreakdownReturn {
  assetBreakdown: (asset: string) => ComputedRef<AssetBreakdown[]>;
  liabilityBreakdown: (asset: string) => ComputedRef<AssetBreakdown[]>;
  locationBreakdown: (identifier: MaybeRef<string>) => ComputedRef<AssetBalanceWithBreakdown[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
}

export function useBalancesBreakdown(): UseBalancesBreakdownReturn {
  const manualStore = useManualBalancesStore();
  const { manualBalanceByLocation } = storeToRefs(manualStore);
  const { assetBreakdown: manualAssetBreakdown, liabilityBreakdown: manualLiabilityBreakdown, getLocationBreakdown: getManualLocationBreakdown } = manualStore;
  const {
    getBreakdown: getExchangeBreakdown,
    getLocationBreakdown: getExchangesLocationBreakdown,
    getByLocationBalances: getExchangesByLocationBalances,
  } = useExchangeBalancesStore();
  const { assetBreakdown: blockchainAssetBreakdown, liabilityBreakdown: blockchainLiabilityBreakdown } = useBlockchainStore();
  const { locationBreakdown: blockchainLocationBreakdown, blockchainTotal } = useBlockchainAggregatedBalances();
  const { toSelectedCurrency, assetPrice } = useBalancePricesStore();
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

  const locationBreakdown = (identifier: MaybeRef<string>): ComputedRef<AssetBalanceWithBreakdown[]> =>
    computed<AssetBalanceWithBreakdown[]>(() => {
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
    liabilityBreakdown,
    locationBreakdown,
    balancesByLocation,
  };
}
