import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';

export const useHistoryStore = defineStore('history', () => {
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const associatedLocations: Ref<string[]> = ref([]);
  const { fetchAssociatedLocations: fetchAssociatedLocationsApi }
    = useHistoryApi();

  const unDecodedTransactionsStatus: Ref<
    Record<string, EvmUnDecodedTransactionsData>
  > = ref({});

  const setUnDecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData) => {
    set(unDecodedTransactionsStatus, {
      ...get(unDecodedTransactionsStatus),
      [data.evmChain]: data,
    });
  };

  const resetUnDecodedTransactionsStatus = () => {
    set(unDecodedTransactionsStatus, {});
  };

  const fetchAssociatedLocations = async () => {
    try {
      set(associatedLocations, await fetchAssociatedLocationsApi());
    }
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        title: t(
          'actions.history.fetch_associated_locations.error.title',
        ).toString(),
        message: t('actions.history.fetch_associated_locations.error.message', {
          message,
        }).toString(),
        display: true,
      });
    }
  };

  return {
    associatedLocations,
    fetchAssociatedLocations,
    unDecodedTransactionsStatus,
    setUnDecodedTransactionsStatus,
    resetUnDecodedTransactionsStatus,
  };
});
