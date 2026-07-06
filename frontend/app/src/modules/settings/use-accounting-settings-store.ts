import type { AccountingSettings } from '@/modules/settings/types/user-settings';
import { toSettingsRefs } from '@/modules/core/common/to-settings-refs';
import { defaultAccountingSettings } from '@/modules/settings/factories';

export const useAccountingSettingsStore = defineStore('settings/accounting', () => {
  const settings = ref(defaultAccountingSettings());

  const refs = toSettingsRefs(settings);

  const update = (accountingSettings: AccountingSettings): void => {
    set(settings, {
      ...get(settings),
      ...accountingSettings,
    });
  };

  return {
    ...refs,
    settings,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAccountingSettingsStore, import.meta.hot));
