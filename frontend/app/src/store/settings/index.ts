import type { ActionStatus } from '@/types/action';
import type { KrakenAccountType } from '@/types/exchanges';
import type { Module } from '@/types/modules';
import type { SettingsUpdate } from '@/types/user';
import { useSettingsApi } from '@/composables/api/settings/settings-api';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { usePremiumStore } from '@/store/session/premium';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { ApiValidationError } from '@/types/api/errors';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

export const useSettingsStore = defineStore('settings', () => {
  const { showErrorMessage, showSuccessMessage } = useNotifications();
  const { addQueriedAddress } = useQueriedAddressesStore();
  const generalStore = useGeneralSettingsStore();
  const accountingStore = useAccountingSettingsStore();
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { t } = useI18n({ useScope: 'global' });

  const api = useSettingsApi();

  const setKrakenAccountType = async (krakenAccountType: KrakenAccountType): Promise<void> => {
    try {
      const { general } = await api.setSettings({
        krakenAccountType,
      });
      generalStore.update(general);
      showSuccessMessage(t('actions.session.kraken_account.success.title'), t('actions.session.kraken_account.success.message'));
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.session.kraken_account.error.title'), getErrorMessage(error));
    }
  };

  function handleErrors(error: unknown, keys: string[]): string {
    if (!(error instanceof ApiValidationError)) {
      return getErrorMessage(error);
    }

    const settingsErrors = error.errors.settings as unknown as Record<string, string | string[]>;

    if (settingsErrors && keys.length === 1 && settingsErrors[keys[0]]) {
      const errorValues = settingsErrors[keys[0]];
      return Array.isArray(errorValues) ? errorValues.join(', ') : errorValues;
    }

    return getErrorMessage(error);
  }

  const update = async (update: SettingsUpdate): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      const {
        accounting,
        general,
        other: { havePremium, premiumShouldSync },
      } = await api.setSettings(update);
      set(premium, havePremium);
      set(premiumSync, premiumShouldSync);
      generalStore.update(general);
      accountingStore.update(accounting);
      success = true;
    }
    catch (error: unknown) {
      logger.error(error);
      message = handleErrors(error, Object.keys(update));
    }
    return {
      message,
      success,
    };
  };

  const enableModule = async (payload: { readonly enable: Module[]; readonly addresses: string[] }): Promise<void> => {
    const activeModules = generalStore.activeModules;
    const modules: Module[] = [...activeModules, ...payload.enable].filter(uniqueStrings);

    await update({ activeModules: modules });

    for (const module of payload.enable) {
      for (const address of payload.addresses) await addQueriedAddress({ address, module });
    }
  };

  return {
    enableModule,
    setKrakenAccountType,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSettingsStore, import.meta.hot));
