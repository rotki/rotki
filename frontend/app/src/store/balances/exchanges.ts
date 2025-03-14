import type {
  ExchangeData,
} from '@/types/exchanges';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import { updateBalancesPrices } from '@/utils/prices';

export const useExchangeBalancesStore = defineStore('balances/exchanges', () => {
  const exchangeBalances = ref<ExchangeData>({});

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    const exchanges = { ...get(exchangeBalances) };
    for (const exchange in exchanges) exchanges[exchange] = updateBalancesPrices(exchanges[exchange], prices);

    set(exchangeBalances, exchanges);
  };

  return {
    exchangeBalances,
    updatePrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useExchangeBalancesStore, import.meta.hot));
