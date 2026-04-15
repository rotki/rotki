import type { Module } from '@/modules/common/modules';
import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { defaultGeneralSettings } from '@/data/factories';
import { useCurrencies } from '@/modules/amount-display/currencies';
import { useGeneralSettingsStore } from '@/store/settings/general';

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
