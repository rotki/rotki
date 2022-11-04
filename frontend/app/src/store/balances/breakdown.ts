import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { ComputedRef } from 'vue';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancePricesStore } from '@/store/balances/prices';
import { AssetBreakdown } from '@/store/balances/types';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';
import { useAggregatedBlockchainBalancesStore } from '@/store/blockchain/balances/aggregated';
import { mergeAssetBalances } from '@/utils/balances';
import { NoPrice, sortDesc } from '@/utils/bignumbers';

export const useBalancesBreakdownStore = defineStore(
  'balances/breakdown',
  () => {
    const manualStore = useManualBalancesStore();
    const { manualBalanceByLocation } = storeToRefs(manualStore);
    const {
      getBreakdown: getManualBreakdown,
      getLocationBreakdown: getManualLocationBreakdown
    } = manualStore;
    const {
      getBreakdown: getExchangeBreakdown,
      getLocationBreakdown: getExchangesLocationBreakdown,
      getByLocationBalances: getExchangesByLocationBalances
    } = useExchangeBalancesStore();
    const { getBreakdown: getBlockchainBreakdown } = useAccountBalancesStore();
    const { locationBreakdown: blockchainLocationBreakdown, blockchainTotal } =
      storeToRefs(useAggregatedBlockchainBalancesStore());
    const { toSelectedCurrency, assetPrice } = useBalancePricesStore();
    const { isAssetIgnored } = useIgnoredAssetsStore();

    const assetBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
      computed(() =>
        get(getBlockchainBreakdown(asset))
          .concat(get(getManualBreakdown(asset)))
          .concat(get(getExchangeBreakdown(asset)))
          .sort((a, b) => sortDesc(a.balance.usdValue, b.balance.usdValue))
      );

    const locationBreakdown = (
      identifier: string
    ): ComputedRef<AssetBalanceWithPrice[]> =>
      computed(() => {
        let balances = mergeAssetBalances(
          get(getManualLocationBreakdown(identifier)),
          get(getExchangesLocationBreakdown(identifier))
        );

        if (identifier === TRADE_LOCATION_BLOCKCHAIN) {
          balances = mergeAssetBalances(
            balances,
            get(blockchainLocationBreakdown)
          );
        }

        return Object.keys(balances)
          .filter(asset => !get(isAssetIgnored(asset)))
          .map(asset => ({
            asset,
            amount: balances[asset].amount,
            usdValue: balances[asset].usdValue,
            usdPrice: get(assetPrice(asset)) ?? NoPrice
          }))
          .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
      });

    const balancesByLocation: ComputedRef<Record<string, BigNumber>> = computed(
      () => {
        const map: Record<string, BigNumber> = {
          [TRADE_LOCATION_BLOCKCHAIN]: get(toSelectedCurrency(blockchainTotal))
        };

        const exchange = get(
          getExchangesByLocationBalances(toSelectedCurrency)
        );
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
      }
    );

    return {
      assetBreakdown,
      locationBreakdown,
      balancesByLocation
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBalancesBreakdownStore, import.meta.hot)
  );
}
