import isEqual from 'lodash/isEqual';
import { Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { api } from '@/services/rotkehlchen-api';
import { useAssociatedLocationsStore } from '@/store/history/associated-locations';
import { TradeEntry } from '@/store/history/types';
import {
  defaultHistoricPayloadState,
  mapCollectionEntriesWithMeta
} from '@/store/history/utils';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Collection, CollectionResponse } from '@/types/collection';
import { SupportedExchange } from '@/types/exchanges';
import { EntryWithMeta } from '@/types/history/meta';
import { TradeLocation } from '@/types/history/trade-location';
import {
  NewTrade,
  Trade,
  TradeCollectionResponse,
  TradeRequestPayload
} from '@/types/history/trades';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { useTradeLocations } from '@/types/trades';
import {
  defaultCollectionState,
  mapCollectionResponse
} from '@/utils/collection';
import { logger } from '@/utils/logging';

export const useTrades = defineStore('history/trades', () => {
  const trades = ref(defaultCollectionState<TradeEntry>()) as Ref<
    Collection<TradeEntry>
  >;

  const tradesPayload: Ref<Partial<TradeRequestPayload>> = ref(
    defaultHistoricPayloadState<Trade>()
  );

  const locationsStore = useAssociatedLocationsStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { fetchAssociatedLocations } = locationsStore;
  const { exchangeName } = useTradeLocations();
  const { tc } = useI18n();

  const fetchTrades = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
      Section.TRADES,
      !!onlyLocation
    );
    const taskType = TaskType.TRADES;

    const fetchTradesHandler = async (
      onlyCache: boolean,
      parameters?: Partial<TradeRequestPayload>
    ) => {
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
        const result = await api.history.trades(payload);
        return mapCollectionEntriesWithMeta<Trade>(
          mapCollectionResponse(result)
        ) as Collection<TradeEntry>;
      }

      const { taskId } = await api.history.tradesTask(payload);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : tc('actions.trades.all_exchanges');
      const taskMeta = {
        title: tc('actions.trades.task.title'),
        description: tc('actions.trades.task.description', undefined, {
          exchange
        }),
        location,
        numericKeys: []
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
      ) as Collection<TradeEntry>;
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

      const fetchOnlyCache = async () => {
        set(trades, await fetchTradesHandler(true));
      };

      setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

      if (!onlyLocation) await fetchOnlyCache();

      if (!onlyCache || onlyLocation) {
        setStatus(Status.REFRESHING);
        const { notify } = useNotifications();

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
  ) => {
    if (!isEqual(get(tradesPayload), newPayload)) {
      set(tradesPayload, newPayload);
      await fetchTrades();
    }
  };

  const addExternalTrade = async (trade: NewTrade): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      await api.history.addExternalTrade(trade);
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
      await api.history.editExternalTrade(trade);
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
      success = await api.history.deleteExternalTrade(tradesIds);
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
