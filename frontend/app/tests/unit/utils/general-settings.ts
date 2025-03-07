import type { Module } from '@/types/modules';
import type { GeneralSettings } from '@/types/user';
import { defaultGeneralSettings } from '@/data/factories';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useCurrencies } from '@/types/currencies';

export function updateGeneralSettings(settings: Partial<GeneralSettings>) {
  const settingsStore = useGeneralSettingsStore();
  const { defaultCurrency } = useCurrencies();

  settingsStore.update({
    ...defaultGeneralSettings(get(defaultCurrency)),
    ...settings,
  });
}

export function setModules(modules: Module[]) {
  updateGeneralSettings({ activeModules: modules });
}
