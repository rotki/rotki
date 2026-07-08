import type { Module } from '@/modules/core/common/modules';
import type { GeneralSettings } from '@/modules/settings/types/user-settings';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

export function updateGeneralSettings(settings: Partial<GeneralSettings>) {
  const settingsStore = useSettingsRepo();
  const { defaultCurrency } = useCurrencies();

  settingsStore.updateGeneral({
    ...defaultGeneralSettings(get(defaultCurrency)),
    ...settings,
  });
}

export function setModules(modules: Module[]) {
  updateGeneralSettings({ activeModules: modules });
}
