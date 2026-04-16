import type { Module } from '@/modules/common/modules';
import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { useCurrencies } from '@/modules/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

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
