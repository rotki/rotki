import type { AssetPrices } from '@/types/prices';
import type { ExchangeRates } from '@/types/user';
import { usePriceApi } from '@/composables/api/balances/price';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';

export const useBalancePricesStore = defineStore('balances/prices', () => {
  const prices = ref<AssetPrices>({});
  const exchangeRates = ref<ExchangeRates>({});
  const assetPricesWithCurrentCurrency = ref<AssetPrices>({});

  const euroCollectionAssets = ref<string[]>([]);
  const euroCollectionAssetsLoaded = ref(false);

  const { notify } = useNotificationsStore();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { queryCachedPrices } = usePriceApi();
  const { t } = useI18n({ useScope: 'global' });

  const assetWithManualPrices = computed(() => Object.entries(prices.value)
    .filter(([, price]) => price.isManualPrice)
    .map(([asset]) => asset));

  watch([exchangeRates, currencySymbol], ([rates, symbol]) => {
    if (Object.keys(rates).length <= 0) {
      return;
    }
    const rate = rates[symbol];
    if (rate && !rate.eq(0)) {
      return;
    }
    notify({
      display: true,
      message: t('missing_exchange_rate.message'),
      title: t('missing_exchange_rate.title'),
    });
  });

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
