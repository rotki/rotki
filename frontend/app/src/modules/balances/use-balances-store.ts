import type { ExchangeData } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import { updateBalancesPrices } from '@/utils/prices';
import { type BigNumber, Zero } from '@rotki/common';

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

export const useBalancesStore = defineStore('balances', () => {
  const manualBalances = ref<ManualBalanceWithValue[]>([]);
  const manualLiabilities = ref<ManualBalanceWithValue[]>([]);

  const exchangeBalances = ref<ExchangeData>({});
  const nonFungibleTotalValue = ref<BigNumber>(Zero);

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    const exchanges = { ...get(exchangeBalances) };
    for (const exchange in exchanges) exchanges[exchange] = updateBalancesPrices(exchanges[exchange], prices);

    set(exchangeBalances, exchanges);

    set(manualBalances, updatePriceData(get(manualBalances), prices));
    set(manualLiabilities, updatePriceData(get(manualLiabilities), prices));
  };

  return {
    exchangeBalances,
    manualBalances,
    manualLiabilities,
    nonFungibleTotalValue,
    updatePrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancesStore, import.meta.hot));
