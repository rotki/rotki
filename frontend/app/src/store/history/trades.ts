import isEqual from 'lodash/isEqual';
import { type Ref } from 'vue';
import { useTradesApi } from '@/services/history/trades';
import { useAssociatedLocationsStore } from '@/store/history/associated-locations';
import { useNotificationsStore } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { type ActionStatus } from '@/store/types';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type SupportedExchange } from '@/types/exchanges';
import { type EntryWithMeta } from '@/types/history/meta';
import { type TradeLocation } from '@/types/history/trade-location';
import {
  type NewTrade,
  type Trade,
  TradeCollectionResponse,
  type TradeEntry,
  type TradeRequestPayload
} from '@/types/history/trades';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { useTradeLocations } from '@/types/trades';
import {
  defaultCollectionState,
  mapCollectionResponse
} from '@/utils/collection';
import { logger } from '@/utils/logging';
import {
  defaultHistoricPayloadState,
  mapCollectionEntriesWithMeta
} from '@/utils/history';

export const useTrades = defineStore('history/trades', () => {
  const trades: Ref<Collection<TradeEntry>> = ref(
    defaultCollectionState<TradeEntry>()
  );

  const tradesPayload: Ref<Partial<TradeRequestPayload>> = ref(
    defaultHistoricPayloadState<Trade>()
  );

  const locationsStore = useAssociatedLocationsStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { fetchAssociatedLocations } = locationsStore;
  const { exchangeName } = useTradeLocations();
  const { tc } = useI18n();
  const { notify } = useNotificationsStore();

  const {
    getTrades,
    getTradesTask,
    addExternalTrade: addExternalTradeCaller,
    editExternalTrade: editExternalTradeCaller,
    deleteExternalTrade: deleteExternalTradeCaller
  } = useTradesApi();

  const fetchTrades = async (
    refresh = false,
    onlyLocation?: SupportedExchange
  ): Promise<void> => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
      Section.TRADES,
      !!onlyLocation
    );
    const taskType = TaskType.TRADES;

    const fetchTradesHandler = async (
      onlyCache: boolean,
      parameters?: Partial<TradeRequestPayload>
    ): Promise<Collection<TradeEntry>> => {
      const defaults: TradeRequestPayload = {
        limit: 0,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache
      };

      const payload: TradeRequestPayload = Object.assign(
        defaults,
        parameters ?? get(tradesPayload)
      );

      if (onlyCache) {
        const result = await getTrades(payload);
        return mapCollectionEntriesWithMeta<Trade>(
          mapCollectionResponse(result)
        );
      }

      const { taskId } = await getTradesTask(payload);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : tc('actions.trades.all_exchanges');
      const taskMeta = {
        title: tc('actions.trades.task.title'),
        description: tc('actions.trades.task.description', undefined, {
          exchange
        }),
        location
      };

      const { result } = await awaitTask<
        CollectionResponse<EntryWithMeta<Trade>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = TradeCollectionResponse.parse(result);
      return mapCollectionEntriesWithMeta<Trade>(
        mapCollectionResponse(parsedResult)
      );
    };

    try {
      const firstLoad = isFirstLoad();
      const onlyCache = firstLoad ? false : !refresh;
      if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
        return;
      }

      if (firstLoad || refresh) {
        await fetchAssociatedLocations();
      }

      const fetchOnlyCache = async (): Promise<void> => {
        set(trades, await fetchTradesHandler(true));
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);

        const locations = onlyLocation
          ? [onlyLocation]
          : get(associatedLocations);

        await Promise.all(
          locations.map(async location => {
            const exchange = exchangeName(location as TradeLocation);
            await fetchTradesHandler(false, { location }).catch(error => {
              notify({
                title: tc('actions.trades.error.title', undefined, {
                  exchange
                }),
                message: tc('actions.trades.error.description', undefined, {
                  exchange,
                  error
                }),
                display: true
              });
            });
          })
        );

        if (!onlyLocation) await fetchOnlyCache();
      }

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );
    } catch (e) {
      logger.error(e);
      resetStatus();
    }
  };

  const updateTradesPayload = async (
    newPayload: Partial<TradeRequestPayload>
  ): Promise<void> => {
    if (!isEqual(get(tradesPayload), newPayload)) {
      set(tradesPayload, newPayload);
      await fetchTrades();
    }
  };

  const addExternalTrade = async (trade: NewTrade): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await addExternalTradeCaller(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchTrades()]);

    return { success, message };
  };

  const editExternalTrade = async (
    trade: TradeEntry
  ): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await editExternalTradeCaller(trade);
      success = true;
    } catch (e: any) {
      message = e.message;
    }

    await Promise.all([fetchAssociatedLocations(), fetchTrades()]);
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

    await Promise.all([fetchAssociatedLocations(), fetchTrades()]);
    return { success, message };
  };

  return {
    trades,
    tradesPayload,
    updateTradesPayload,
    fetchTrades,
    addExternalTrade,
    editExternalTrade,
    deleteExternalTrade
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTrades, import.meta.hot));
}
