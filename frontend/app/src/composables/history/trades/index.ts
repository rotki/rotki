import type { ActionStatus } from '@/types/action';
import type { Collection, CollectionResponse } from '@/types/collection';
import type { EntryWithMeta } from '@/types/history/meta';
import type { NewTrade, Trade, TradeEntry, TradeRequestPayload } from '@/types/history/trade';
import type { TaskMeta } from '@/types/task';
import type { MaybeRef } from '@vueuse/core';
import { useTradesApi } from '@/composables/api/history/trades';
import { useLocations } from '@/composables/locations';
import { useStatusUpdater } from '@/composables/status';
import { useHistoryStore } from '@/store/history';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { mapCollectionResponse } from '@/utils/collection';
import { mapCollectionEntriesWithMeta } from '@/utils/history';
import { logger } from '@/utils/logging';

interface UseTradesReturn {
  refreshTrades: (userInitiated?: boolean, location?: string) => Promise<void>;
  fetchTrades: (payload: MaybeRef<TradeRequestPayload>) => Promise<Collection<TradeEntry>>;
  addExternalTrade: (trade: NewTrade) => Promise<ActionStatus<ValidationErrors | string>>;
  editExternalTrade: (trade: Trade) => Promise<ActionStatus<ValidationErrors | string>>;
  deleteExternalTrade: (tradesIds: string[]) => Promise<ActionStatus>;
}

export function useTrades(): UseTradesReturn {
  const { fetchAssociatedLocations } = useHistoryStore();
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { exchangeName } = useLocations();
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    addExternalTrade: addExternalTradeCaller,
    deleteExternalTrade: deleteExternalTradeCaller,
    editExternalTrade: editExternalTradeCaller,
    getTrades,
    getTradesTask,
  } = useTradesApi();

  const syncTradesTask = async (location: string): Promise<boolean> => {
    const taskType = TaskType.TRADES;

    const defaults: TradeRequestPayload = {
      ascending: [false],
      limit: 0,
      location,
      offset: 0,
      onlyCache: false,
      orderByAttributes: ['timestamp'],
    };

    const { taskId } = await getTradesTask(defaults);
    const exchange = exchangeName(location);
    const taskMeta = {
      description: t('actions.trades.task.description', {
        exchange,
      }),
      location,
      title: t('actions.trades.task.title'),
    };

    try {
      await awaitTask<CollectionResponse<EntryWithMeta<Trade>>, TaskMeta>(taskId, taskType, taskMeta, true);
      return true;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.trades.error.description', {
            error: error.message,
            exchange,
          }),
          title: t('actions.trades.error.title', {
            exchange,
          }),
        });
      }
    }

    return false;
  };

  const refreshTrades = async (userInitiated = false, location?: string): Promise<void> => {
    const { fetchDisabled, isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.TRADES);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping trade refresh');
      return;
    }

    await fetchAssociatedLocations();
    const locations = location ? [location] : get(connectedExchanges).map(x => x.location);

    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
      await awaitParallelExecution(locations, location => location, async (location) => {
        await syncTradesTask(location);
      }, 2);
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
    return { message, success };
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
    return { message, success };
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
    return { message, success };
  };

  return {
    addExternalTrade,
    deleteExternalTrade,
    editExternalTrade,
    fetchTrades,
    refreshTrades,
  };
}
