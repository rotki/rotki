import { type Module } from '@/types/modules';
import { useCurrencies } from '@/types/currencies';
import { defaultGeneralSettings } from '@/data/factories';
import { type GeneralSettings } from '@/types/user';

export const updateGeneralSettings = (settings: Partial<GeneralSettings>) => {
  const settingsStore = useGeneralSettingsStore();
  const { defaultCurrency } = useCurrencies();

  settingsStore.update({
    ...defaultGeneralSettings(get(defaultCurrency)),
    ...settings
  });
};

export const setModules = (modules: Module[]) => {
  updateGeneralSettings({ activeModules: modules });
};
