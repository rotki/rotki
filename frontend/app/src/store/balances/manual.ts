import type {
  ManualBalanceWithValue,
} from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';

export const useManualBalancesStore = defineStore('balances/manual', () => {
  const manualBalances = ref<ManualBalanceWithValue[]>([]);
  const manualLiabilities = ref<ManualBalanceWithValue[]>([]);

  function updatePriceData(data: ManualBalanceWithValue[], prices: MaybeRef<AssetPrices>): ManualBalanceWithValue[] {
    return data.map((item) => {
      const assetPrice = get(prices)[item.asset];
      if (!assetPrice)
        return item;

      return {
        ...item,
        usdValue: item.amount.times(assetPrice.usdPrice ?? assetPrice.value),
      };
    });
  }

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    set(manualBalances, updatePriceData(get(manualBalances), prices));
    set(manualLiabilities, updatePriceData(get(manualLiabilities), prices));
  };

  return {
    manualBalances,
    manualLiabilities,
    updatePrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useManualBalancesStore, import.meta.hot));
