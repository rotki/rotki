import { get } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { computed, reactive, toRefs } from 'vue';
import { defaultGeneralSettings } from '@/data/factories';
import { GeneralSettings } from '@/types/user';

export const useGeneralSettingsStore = defineStore('settings/general', () => {
  const settings = reactive(defaultGeneralSettings());
  const refs = toRefs(settings);

  const currencySymbol = computed(() => {
    const currency = get(refs.mainCurrency);
    return currency.tickerSymbol;
  });

  const floatingPrecision = computed(() => settings.uiFloatingPrecision);
  const currency = computed(() => settings.mainCurrency);

  const update = (generalSettings: GeneralSettings) => {
    Object.assign(settings, generalSettings);
  };

  const reset = () => {
    Object.assign(settings, defaultGeneralSettings());
  };

  return {
    ...refs,
    floatingPrecision,
    currency,
    currencySymbol,
    update,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useGeneralSettingsStore, import.meta.hot)
  );
}
