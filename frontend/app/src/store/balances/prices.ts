import type { AssetPrices } from '@/types/prices';
import type { ExchangeRates } from '@/types/user';
import { usePriceApi } from '@/composables/api/balances/price';
import { useGeneralSettingsStore } from '@/store/settings/general';

export const useBalancePricesStore = defineStore('balances/prices', () => {
  const prices = ref<AssetPrices>({});
  const exchangeRates = ref<ExchangeRates>({});
  const assetPricesWithCurrentCurrency = ref<AssetPrices>({});

  const euroCollectionAssets = ref<string[]>([]);
  const euroCollectionAssetsLoaded = ref(false);

  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { queryCachedPrices } = usePriceApi();

  const assetWithManualPrices = computed(() => Object.entries(prices.value)
    .filter(([, price]) => price.isManualPrice)
    .map(([asset]) => asset));

  watch([assetWithManualPrices, currencySymbol], async ([assets, symbol]) => {
    if (assets.length === 0)
      return;

    set(assetPricesWithCurrentCurrency, await queryCachedPrices(assets, symbol));
  });

  return {
    assetPricesWithCurrentCurrency,
    euroCollectionAssets,
    euroCollectionAssetsLoaded,
    exchangeRates,
    prices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancePricesStore, import.meta.hot));
