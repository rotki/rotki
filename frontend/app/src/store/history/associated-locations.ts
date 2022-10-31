import { Ref } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { TradeLocation } from '@/types/history/trade-location';
import { logger } from '@/utils/logging';

export const useAssociatedLocationsStore = defineStore(
  'history/associated-locations',
  () => {
    const { notify } = useNotifications();
    const { t } = useI18n();
    const associatedLocations: Ref<TradeLocation[]> = ref([]);
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

    const reset = () => {
      set(associatedLocations, []);
    };

    return {
      associatedLocations,
      fetchAssociatedLocations,
      reset
    };
  }
);
