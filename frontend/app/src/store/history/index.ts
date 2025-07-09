import type { EvmUnDecodedTransactionsData, ProtocolCacheUpdatesData } from '@/types/websocket-messages';
import { useHistoryApi } from '@/composables/api/history';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { TransactionChainType } from '@/types/history/events';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

export const useHistoryStore = defineStore('history', () => {
  const associatedLocations = ref<string[]>([]);
  const undecodedTransactionsStatus = ref<Record<string, EvmUnDecodedTransactionsData>>({});
  const protocolCacheUpdateStatus = ref<Record<string, ProtocolCacheUpdatesData>>({});
  const evmTransactionStatus = ref<{ lastQueriedTs: number; pendingDecode: boolean }>();

  const receivingProtocolCacheStatus = ref<boolean>(false);

  const { useIsTaskRunning } = useTaskStore();
  const { getChain, isEvmLikeChains } = useSupportedChains();
  const { getEvmTransactionStatus } = useHistoryEventsApi();

  const decodingStatus = computed<EvmUnDecodedTransactionsData[]>(() =>
    Object.values(get(undecodedTransactionsStatus)).filter(status => status.total > 0),
  );

  const protocolCacheStatus = computed<ProtocolCacheUpdatesData[]>(() =>
    Object.values(get(protocolCacheUpdateStatus)).filter(status => status.total > 0),
  );

  const setUndecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData): void => {
    set(receivingProtocolCacheStatus, false);
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      [data.chain]: data,
    });
  };

  const updateUndecodedTransactionsStatus = (data: Record<string, EvmUnDecodedTransactionsData>): void => {
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      ...data,
    });
  };

  const refreshProtocolCacheTaskRunning = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);

  const setProtocolCacheStatus = (data: ProtocolCacheUpdatesData): void => {
    set(receivingProtocolCacheStatus, true);
    const old = get(protocolCacheUpdateStatus);
    const filtered: Record<string, ProtocolCacheUpdatesData> = {};
    const currentKey = `${data.chain}#${data.protocol}`;
    for (const key in old) {
      if (key !== currentKey) {
        filtered[key] = {
          ...old[key],
          processed: old[key].total,
        };
      }
    }
    set(protocolCacheUpdateStatus, {
      [currentKey]: data,
      ...filtered,
    });
  };

  const resetUndecodedTransactionsStatus = (): void => {
    set(undecodedTransactionsStatus, {});
  };

  const clearUndecodedTransactionsNumbers = (type: TransactionChainType): void => {
    const currentStatus = get(undecodedTransactionsStatus);
    const newStatus: Record<string, EvmUnDecodedTransactionsData> = {};

    for (const [chain, value] of Object.entries(currentStatus)) {
      const blockchain = getChain(chain);
      const isEvmLike = isEvmLikeChains(blockchain);

      if ((isEvmLike && type === TransactionChainType.EVMLIKE) || (!isEvmLike && type === TransactionChainType.EVM)) {
        newStatus[chain] = {
          ...value,
          processed: value.total,
        };
      }
      else {
        newStatus[chain] = {
          ...value,
        };
      }
    }
    set(undecodedTransactionsStatus, newStatus);
  };

  const resetProtocolCacheUpdatesStatus = (): void => {
    set(protocolCacheUpdateStatus, {});
    set(receivingProtocolCacheStatus, false);
  };

  const { fetchAssociatedLocations: fetchAssociatedLocationsApi } = useHistoryApi();
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const getUndecodedTransactionStatus = (): EvmUnDecodedTransactionsData[] =>
    Object.values(get(undecodedTransactionsStatus));

  const fetchAssociatedLocations = async (): Promise<void> => {
    try {
      set(associatedLocations, await fetchAssociatedLocationsApi());
    }
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        display: true,
        message: t('actions.history.fetch_associated_locations.error.message', { message }),
        title: t('actions.history.fetch_associated_locations.error.title'),
      });
    }
  };

  const fetchEvmTransactionStatus = async (): Promise<void> => {
    try {
      const result = await getEvmTransactionStatus();
      set(evmTransactionStatus, result);
    }
    catch (error: any) {
      logger.error(error);
    }
  };

  watch(refreshProtocolCacheTaskRunning, (curr, prev) => {
    if (!curr && prev) {
      resetProtocolCacheUpdatesStatus();
    }
  });

  return {
    associatedLocations,
    clearUndecodedTransactionsNumbers,
    decodingStatus,
    evmTransactionStatus,
    fetchAssociatedLocations,
    fetchEvmTransactionStatus,
    getUndecodedTransactionStatus,
    protocolCacheStatus,
    receivingProtocolCacheStatus,
    resetProtocolCacheUpdatesStatus,
    resetUndecodedTransactionsStatus,
    setProtocolCacheStatus,
    setUndecodedTransactionsStatus,
    undecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  };
});
