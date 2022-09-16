import { set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { Ref, ref } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { IgnoredActions } from '@/services/history/const';
import { TradeLocation } from '@/services/history/types';
import { api } from '@/services/rotkehlchen-api';
import { ALL_CENTRALIZED_EXCHANGES } from '@/services/session/consts';
import { Section } from '@/store/const';
import { useAssetMovements } from '@/store/history/asset-movements';
import { useLedgerActions } from '@/store/history/ledger-actions';
import { useTrades } from '@/store/history/trades';
import { useTransactions } from '@/store/history/transactions';
import { IgnoreActionPayload } from '@/store/history/types';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import { ActionStatus } from '@/store/types';
import { getStatusUpdater } from '@/store/utils';
import { SupportedExchange } from '@/types/exchanges';
import { logger } from '@/utils/logging';

export const useHistory = defineStore('history', () => {
  const associatedLocations: Ref<TradeLocation[]> = ref([]);
  const ignored = ref<IgnoredActions>({});

  const { notify } = useNotifications();
  const { setMessage } = useMessageStore();
  const { t } = useI18n();

  const fetchAssociatedLocations = async () => {
    try {
      set(associatedLocations, await api.history.associatedLocations());
    } catch (e: any) {
      logger.error(e);
      const message = e?.message ?? e ?? '';
      notify({
        title: t(
          'actions.history.fetch_associated_locations.error.title'
        ).toString(),
        message: t('actions.history.fetch_associated_locations.error.message', {
          message
        }).toString(),
        display: true
      });
    }
  };

  const fetchIgnored = async () => {
    try {
      set(ignored, await api.history.fetchIgnored());
    } catch (e: any) {
      logger.error(e);
      const message = e?.message ?? e ?? '';
      notify({
        title: t('actions.history.fetch_ignored.error.title').toString(),
        message: t('actions.history.fetch_ignored.error.message', {
          message
        }).toString(),
        display: true
      });
    }
  };

  const ignoreInAccounting = async (
    { actionIds, type }: IgnoreActionPayload,
    ignore: boolean
  ): Promise<ActionStatus> => {
    try {
      ignore
        ? await api.ignoreActions(actionIds, type)
        : await api.unignoreActions(actionIds, type);
      await fetchIgnored();
    } catch (e: any) {
      let title: string;
      let description: string;
      if (ignore) {
        title = t('actions.ignore.error.title').toString();
      } else {
        title = t('actions.unignore.error.title').toString();
      }

      if (ignore) {
        description = t('actions.ignore.error.description', {
          error: e.message
        }).toString();
      } else {
        description = t('actions.unignore.error.description', {
          error: e.message
        }).toString();
      }
      setMessage({
        success: false,
        title,
        description
      });
      return { success: false, message: 'failed' };
    }

    return { success: true };
  };

  // Purge
  const purgeHistoryLocation = async (exchange: SupportedExchange) => {
    const { fetchTrades } = useTrades();
    const { fetchAssetMovements } = useAssetMovements();
    const { fetchLedgerActions } = useLedgerActions();
    await Promise.allSettled([
      fetchTrades(true, exchange),
      fetchAssetMovements(true, exchange),
      fetchLedgerActions(true, exchange)
    ]);
  };

  const purgeExchange = async (
    exchange: SupportedExchange | typeof ALL_CENTRALIZED_EXCHANGES
  ) => {
    const { resetStatus } = getStatusUpdater(Section.TRADES);

    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      resetStatus();
      resetStatus(Section.ASSET_MOVEMENT);
      resetStatus(Section.LEDGER_ACTIONS);
    } else {
      await purgeHistoryLocation(exchange);
    }
  };

  // Reset
  const reset = () => {
    set(associatedLocations, []);
    set(ignored, {});
    useTrades().reset();
    useAssetMovements().reset();
    useTransactions().reset();
    useLedgerActions().reset();
  };

  return {
    associatedLocations,
    ignored,
    fetchAssociatedLocations,
    fetchIgnored,
    ignoreInAccounting,
    purgeExchange,
    purgeHistoryLocation,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useHistory, import.meta.hot));
}
