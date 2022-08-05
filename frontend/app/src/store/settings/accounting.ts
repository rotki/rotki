import { reactive, toRefs } from '@vue/composition-api';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { defaultAccountingSettings } from '@/data/factories';
import { AccountingSettings } from '@/types/user';

export const useAccountingSettingsStore = defineStore(
  'settings/accounting',
  () => {
    const settings = reactive(defaultAccountingSettings());

    const update = (accountingSettings: AccountingSettings) => {
      Object.assign(settings, accountingSettings);
    };

    const reset = () => {
      Object.assign(settings, defaultAccountingSettings());
    };

    return {
      ...toRefs(settings),
      update,
      reset
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAccountingSettingsStore, import.meta.hot)
  );
}
