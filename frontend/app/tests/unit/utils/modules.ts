import { type Module } from '@/types/modules';
import { useCurrencies } from '@/types/currencies';
import { defaultGeneralSettings } from '@/data/factories';

export const setModules = (modules: Module[]) => {
  const settingsStore = useGeneralSettingsStore();
  const { defaultCurrency } = useCurrencies();

  settingsStore.update({
    ...defaultGeneralSettings(get(defaultCurrency)),
    activeModules: modules
  });
};
