import { useSettingsApi } from '@/services/settings/settings-api';
import { useMessageStore } from '@/store/message';
import { usePremiumStore } from '@/store/session/premium';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { ActionStatus } from '@/store/types';
import { KrakenAccountType } from '@/types/exchanges';
import { Module } from '@/types/modules';
import { SettingsUpdate } from '@/types/user';
import { uniqueStrings } from '@/utils/data';

export const useSettingsStore = defineStore('settings', () => {
  const { setMessage } = useMessageStore();
  const { addQueriedAddress } = useQueriedAddressesStore();
  const generalStore = useGeneralSettingsStore();
  const accountingStore = useAccountingSettingsStore();
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { t } = useI18n();

  const api = useSettingsApi();

  const setKrakenAccountType = async (krakenAccountType: KrakenAccountType) => {
    try {
      const { general } = await api.setSettings({
        krakenAccountType
      });
      generalStore.update(general);
      setMessage({
        title: t('actions.session.kraken_account.success.title').toString(),
        description: t(
          'actions.session.kraken_account.success.message'
        ).toString(),
        success: true
      });
    } catch (e: any) {
      setMessage({
        title: t('actions.session.kraken_account.error.title').toString(),
        description: e.message
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
        other: { havePremium, premiumShouldSync }
      } = await api.setSettings(update);
      set(premium, havePremium);
      set(premiumSync, premiumShouldSync);
      generalStore.update(general);
      accountingStore.update(accounting);
      success = true;
    } catch (e: any) {
      message = e.message;
    }
    return {
      success,
      message
    };
  };

  const enableModule = async (payload: {
    readonly enable: Module[];
    readonly addresses: string[];
  }) => {
    const activeModules = generalStore.activeModules;
    const modules: Module[] = [...activeModules, ...payload.enable].filter(
      uniqueStrings
    );

    await update({ activeModules: modules });

    for (const module of payload.enable) {
      for (const address of payload.addresses) {
        await addQueriedAddress({ module, address });
      }
    }
  };

  return {
    setKrakenAccountType,
    enableModule,
    update
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSettingsStore, import.meta.hot));
}
