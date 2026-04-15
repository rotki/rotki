import type { SupportedCurrency } from '@/modules/amount-display/currencies';
import type { AssetPrices } from '@/modules/prices/price-types';
import type { ExchangeRates } from '@/modules/settings/types/user-settings';

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
