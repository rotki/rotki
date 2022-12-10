import { type Ref } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { useNotificationsStore } from '@/store/notifications';
import { type TradeLocation } from '@/types/history/trade-location';
import { logger } from '@/utils/logging';

export const useAssociatedLocationsStore = defineStore(
  'history/associated-locations',
  () => {
    const { notify } = useNotificationsStore();
    const { t } = useI18n();
    const associatedLocations: Ref<TradeLocation[]> = ref([]);
    const fetchAssociatedLocations = async (): Promise<void> => {
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

    return {
      associatedLocations,
      fetchAssociatedLocations
    };
  }
);
