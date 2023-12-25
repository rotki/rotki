import { type EvmUndecodedTransactionsData } from '@/types/websocket-messages';

export const useHistoryStore = defineStore('history', () => {
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const associatedLocations: Ref<string[]> = ref([]);
  const { fetchAssociatedLocations: fetchAssociatedLocationsApi } =
    useHistoryApi();

  const evmUndecodedTransactionsStatus: Ref<
    Record<string, EvmUndecodedTransactionsData>
  > = ref({});

  const setEvmUndecodedTransactions = (data: EvmUndecodedTransactionsData) => {
    set(evmUndecodedTransactionsStatus, {
      ...get(evmUndecodedTransactionsStatus),
      [data.evmChain]: data
    });
  };

  const resetEvmUndecodedTransactionsStatus = () => {
    set(evmUndecodedTransactionsStatus, {});
  };

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

  return {
    associatedLocations,
    fetchAssociatedLocations,
    evmUndecodedTransactionsStatus,
    setEvmUndecodedTransactions,
    resetEvmUndecodedTransactionsStatus
  };
});
