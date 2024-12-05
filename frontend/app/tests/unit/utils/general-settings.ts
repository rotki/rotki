import { useCurrencies } from '@/types/currencies';
import { defaultGeneralSettings } from '@/data/factories';
import { useGeneralSettingsStore } from '@/store/settings/general';
import type { Module } from '@/types/modules';
import type { GeneralSettings } from '@/types/user';

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
