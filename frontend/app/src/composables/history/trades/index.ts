import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import type { MaybeRef } from '@vueuse/core';
import type { Collection, CollectionResponse } from '@/types/collection';
import type { EntryWithMeta } from '@/types/history/meta';
import type { NewTrade, Trade, TradeEntry, TradeRequestPayload } from '@/types/history/trade';
import type { TaskMeta } from '@/types/task';
import type { ActionStatus } from '@/types/action';

interface UseTradesReturn {
  refreshTrades: (userInitiated?: boolean, location?: string) => Promise<void>;
  fetchTrades: (payload: MaybeRef<TradeRequestPayload>) => Promise<Collection<TradeEntry>>;
  addExternalTrade: (trade: NewTrade) => Promise<ActionStatus<ValidationErrors | string>>;
  editExternalTrade: (trade: Trade) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteExternalTrade: (tradesIds: string[]) => Promise<ActionStatus>;
}

export function useTrades(): UseTradesReturn {
  const { fetchAssociatedLocations } = useHistoryStore();
  const { connectedExchanges } = storeToRefs(useExchangesStore());
  const { exchangeName } = useLocations();
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    getTrades,
    getTradesTask,
    addExternalTrade: addExternalTradeCaller,
    editExternalTrade: editExternalTradeCaller,
    deleteExternalTrade: deleteExternalTradeCaller,
  } = useTradesApi();

  const syncTradesTask = async (location: string): Promise<boolean> => {
    const taskType = TaskType.TRADES;

    const defaults: TradeRequestPayload = {
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false,
      location,
    };

    const { taskId } = await getTradesTask(defaults);
    const exchange = exchangeName(location);
    const taskMeta = {
      title: t('actions.trades.task.title'),
      description: t('actions.trades.task.description', {
        exchange,
      }),
      location,
    };

    try {
      await awaitTask<CollectionResponse<EntryWithMeta<Trade>>, TaskMeta>(taskId, taskType, taskMeta, true);
      return true;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.trades.error.title', {
            exchange,
          }),
          message: t('actions.trades.error.description', {
            exchange,
            error: error.message,
          }),
          display: true,
        });
      }
    }

    return false;
  };

  const refreshTrades = async (userInitiated = false, location?: string): Promise<void> => {
    const { setStatus, isFirstLoad, resetStatus, fetchDisabled } = useStatusUpdater(Section.TRADES);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping trade refresh');
      return;
    }

    await fetchAssociatedLocations();
    const locations = location ? [location] : get(connectedExchanges).map(x => x.location);

    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
      await Promise.all(locations.map(syncTradesTask));
      await fetchAssociatedLocations();
      setStatus(Status.LOADED);
    }
    catch (error: any) {
      logger.error(error);
      resetStatus();
    }
  };

  const fetchTrades = async (payload: MaybeRef<TradeRequestPayload>): Promise<Collection<TradeEntry>> => {
    const result = await getTrades({
      ...get(payload),
      onlyCache: true,
    });
    return mapCollectionEntriesWithMeta<Trade>(mapCollectionResponse(result));
  };

  const addExternalTrade = async (trade: NewTrade): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addExternalTradeCaller(trade);
      success = true;
    }
    catch (error: any) {
      message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(trade);
    }

    await fetchAssociatedLocations();
    return { success, message };
  };

  const editExternalTrade = async (trade: Trade): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await editExternalTradeCaller(trade);
      success = true;
    }
    catch (error: any) {
      message = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors(trade);
    }

    await fetchAssociatedLocations();
    return { success, message };
  };

  const deleteExternalTrade = async (tradesIds: string[]): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      success = await deleteExternalTradeCaller(tradesIds);
    }
    catch (error: any) {
      message = error.message;
    }

    await fetchAssociatedLocations();
    return { success, message };
  };

  return {
    refreshTrades,
    fetchTrades,
    addExternalTrade,
    editExternalTrade,
    deleteExternalTrade,
  };
}
