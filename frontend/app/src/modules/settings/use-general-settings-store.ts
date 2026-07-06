import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { type SupportedCurrency, useCurrencies } from '@/modules/assets/amount-display/currencies';
import { toSettingsRefs } from '@/modules/core/common/to-settings-refs';
import { defaultGeneralSettings } from '@/modules/settings/factories';

export const useGeneralSettingsStore = defineStore('settings/general', () => {
  const { defaultCurrency } = useCurrencies();
  const settings = ref(defaultGeneralSettings(get(defaultCurrency)));

  // `mainCurrency` and `uiFloatingPrecision` are exposed under the renamed public keys `currency`
  // and `floatingPrecision`, so they are pulled out of the derived refs and re-added below rather
  // than spread under their raw names.
  const { mainCurrency, uiFloatingPrecision, ...refs } = toSettingsRefs(settings);

  const currencySymbol = computed<SupportedCurrency>(() => get(mainCurrency).tickerSymbol);

  const update = (generalSettings: GeneralSettings): void => {
    set(settings, {
      ...get(settings),
      ...generalSettings,
    });
  };

  return {
    ...refs,
    currency: mainCurrency,
    currencySymbol,
    floatingPrecision: uiFloatingPrecision,
    settings,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useGeneralSettingsStore, import.meta.hot));
