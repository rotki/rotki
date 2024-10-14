import type { KrakenAccountType } from '@/types/exchanges';
import type { Module } from '@/types/modules';
import type { SettingsUpdate } from '@/types/user';
import type { ActionStatus } from '@/types/action';

export const useSettingsStore = defineStore('settings', () => {
  const { setMessage } = useMessageStore();
  const { addQueriedAddress } = useQueriedAddressesStore();
  const generalStore = useGeneralSettingsStore();
  const accountingStore = useAccountingSettingsStore();
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { t } = useI18n();

  const api = useSettingsApi();

  const setKrakenAccountType = async (krakenAccountType: KrakenAccountType): Promise<void> => {
    try {
      const { general } = await api.setSettings({
        krakenAccountType,
      });
      generalStore.update(general);
      setMessage({
        title: t('actions.session.kraken_account.success.title'),
        description: t('actions.session.kraken_account.success.message'),
        success: true,
      });
    }
    catch (error: any) {
      setMessage({
        title: t('actions.session.kraken_account.error.title'),
        description: error.message,
      });
    }
  };

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
    catch (error: any) {
      logger.error(error);
      message = error.message;
    }
    return {
      success,
      message,
    };
  };

  const enableModule = async (payload: { readonly enable: Module[]; readonly addresses: string[] }): Promise<void> => {
    const activeModules = generalStore.activeModules;
    const modules: Module[] = [...activeModules, ...payload.enable].filter(uniqueStrings);

    await update({ activeModules: modules });

    for (const module of payload.enable) {
      for (const address of payload.addresses) await addQueriedAddress({ module, address });
    }
  };

  return {
    setKrakenAccountType,
    enableModule,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSettingsStore, import.meta.hot));
