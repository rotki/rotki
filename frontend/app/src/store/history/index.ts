import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';

export const useHistoryStore = defineStore('history', () => {
  const associatedLocations = ref<string[]>([]);
  const undecodedTransactionsStatus = ref<Record<string, EvmUnDecodedTransactionsData>>({});

  const decodingStatus = computed<EvmUnDecodedTransactionsData[]>(() => Object.values(get(undecodedTransactionsStatus))
    .filter(status => status.total > 0));

  const setUndecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData) => {
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      [data.evmChain]: data,
    });
  };

  const updateUndecodedTransactionsStatus = (data: Record<string, EvmUnDecodedTransactionsData>): void => {
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      ...data,
    });
  };

  const resetUndecodedTransactionsStatus = () => {
    set(undecodedTransactionsStatus, {});
  };

  const { fetchAssociatedLocations: fetchAssociatedLocationsApi } = useHistoryApi();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const getUndecodedTransactionStatus = (): EvmUnDecodedTransactionsData[] => Object.values(get(undecodedTransactionsStatus));

  const fetchAssociatedLocations = async () => {
    try {
      set(associatedLocations, await fetchAssociatedLocationsApi());
    }
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        title: t('actions.history.fetch_associated_locations.error.title'),
        message: t('actions.history.fetch_associated_locations.error.message', { message }),
        display: true,
      });
    }
  };

  return {
    associatedLocations,
    decodingStatus,
    undecodedTransactionsStatus,
    setUndecodedTransactionsStatus,
    getUndecodedTransactionStatus,
    updateUndecodedTransactionsStatus,
    resetUndecodedTransactionsStatus,
    fetchAssociatedLocations,
  };
});
