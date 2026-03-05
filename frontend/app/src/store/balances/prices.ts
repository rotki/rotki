import type { SupportedCurrency } from '@/types/currencies';
import type { AssetPrices } from '@/types/prices';
import type { ExchangeRates } from '@/types/user';

export const useBalancePricesStore = defineStore('balances/prices', () => {
  const prices = shallowRef<AssetPrices>({});
  const exchangeRates = shallowRef<ExchangeRates>({});
  const previousCurrency = ref<SupportedCurrency>();

  return {
    exchangeRates,
    previousCurrency,
    prices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancePricesStore, import.meta.hot));
