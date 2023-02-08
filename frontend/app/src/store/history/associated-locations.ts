import { type Ref } from 'vue';
import { type TradeLocation } from '@/types/history/trade/location';
import { logger } from '@/utils/logging';
import { type Exchange } from '@/types/exchanges';

export const useAssociatedLocationsStore = defineStore(
  'history/associated-locations',
  () => {
    const { notify } = useNotificationsStore();
    const { t } = useI18n();
    const associatedLocations: Ref<TradeLocation[]> = ref([]);
    const connectedExchanges: Ref<Exchange[]> = ref([]);
    const { fetchAssociatedLocations: fetchAssociatedLocationsApi } =
      useHistoryApi();

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
          message: t(
            'actions.history.fetch_associated_locations.error.message',
            {
              message
            }
          ).toString(),
          display: true
        });
      }
    };

    return {
      connectedExchanges,
      associatedLocations,
      fetchAssociatedLocations
    };
  }
);
