import { type MaybeRef } from '@vueuse/core';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type SupportedExchange } from '@/types/exchanges';
import { type EntryWithMeta } from '@/types/history/meta';
import {
  type NewTrade,
  type Trade,
  type TradeEntry,
  type TradeRequestPayload
} from '@/types/history/trade';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

export const useTrades = () => {
  const { fetchAssociatedLocations } = useHistoryStore();
  const { connectedExchanges } = storeToRefs(useExchangesStore());
  const { exchangeName } = useTradeLocations();
  const { awaitTask } = useTaskStore();
  const { tc } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    getTrades,
    getTradesTask,
    addExternalTrade: addExternalTradeCaller,
    editExternalTrade: editExternalTradeCaller,
    deleteExternalTrade: deleteExternalTradeCaller
  } = useTradesApi();

  const syncTradesTask = async (
    location: SupportedExchange
  ): Promise<boolean> => {
    const taskType = TaskType.TRADES;

    const defaults: TradeRequestPayload = {
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false,
      location
    };

    const { taskId } = await getTradesTask(defaults);
    const exchange = exchangeName(location);
    const taskMeta = {
      title: tc('actions.trades.task.title'),
      description: tc('actions.trades.task.description', undefined, {
        exchange
      }),
      location
    };

    try {
      await awaitTask<CollectionResponse<EntryWithMeta<Trade>>, TaskMeta>(
        taskId,
        taskType,
        taskMeta,
        true
      );
      return true;
    } catch (e: any) {
      notify({
        title: tc('actions.trades.error.title', 0, {
          exchange
        }),
        message: tc('actions.trades.error.description', 0, {
          exchange,
          error: e.message
        }),
        display: true
      });
    }

    return false;
  };

  const refreshTrades = async (
    userInitiated = false,
    location?: SupportedExchange
  ): Promise<void> => {
    const { setStatus, isFirstLoad, resetStatus, fetchDisabled } =
      useStatusUpdater(Section.TRADES);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping trade refresh');
      return;
    }

    await fetchAssociatedLocations();
    const locations = location
      ? [location]
      : get(connectedExchanges).map(x => x.location);

    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
      await Promise.all(locations.map(syncTradesTask));
      await fetchAssociatedLocations();
      setStatus(Status.LOADED);
    } catch (e: any) {
      logger.error(e);
      resetStatus();
    }
  };

  const fetchTrades = async (
    payload: MaybeRef<TradeRequestPayload>
  ): Promise<Collection<TradeEntry>> => {
    const result = await getTrades({
      ...get(payload),
      onlyCache: true
    });
    return mapCollectionEntriesWithMeta<Trade>(mapCollectionResponse(result));
  };

  const addExternalTrade = async (
    trade: NewTrade
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addExternalTradeCaller(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
      if (e instanceof ApiValidationError) {
        message = e.getValidationErrors(trade);
      }
    }

    await fetchAssociatedLocations();
    return { success, message };
  };

  const editExternalTrade = async (
    trade: TradeEntry
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await editExternalTradeCaller(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
      if (e instanceof ApiValidationError) {
        message = e.getValidationErrors(trade);
      }
    }

    await fetchAssociatedLocations();
    return { success, message };
  };

  const deleteExternalTrade = async (
    tradesIds: string[]
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      success = await deleteExternalTradeCaller(tradesIds);
    } catch (e: any) {
      message = e.message;
    }

    await fetchAssociatedLocations();
    return { success, message };
  };

  return {
    refreshTrades,
    fetchTrades,
    addExternalTrade,
    editExternalTrade,
    deleteExternalTrade
  };
};
