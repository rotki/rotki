import { type Ref } from 'vue';
import { type TradeLocation } from '@/types/history/trade/location';
import { logger } from '@/utils/logging';
import { type Exchange } from '@/types/exchanges';

export const useHistoryStore = defineStore('history', () => {
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const counterparties: Ref<string[]> = ref([]);
  const associatedLocations: Ref<TradeLocation[]> = ref([]);
  const connectedExchanges: Ref<Exchange[]> = ref([]);
  const {
    fetchAssociatedLocations: fetchAssociatedLocationsApi,
    fetchAvailableCounterparties
  } = useHistoryApi();

  const fetchAssociatedLocations = async () => {
    try {
      set(associatedLocations, await fetchAssociatedLocationsApi());
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

  const fetchCounterparties = async (): Promise<void> => {
    const result = await fetchAvailableCounterparties();

    set(counterparties, result);
  };

  return {
    counterparties,
    connectedExchanges,
    associatedLocations,
    fetchAssociatedLocations,
    fetchCounterparties
  };
});
