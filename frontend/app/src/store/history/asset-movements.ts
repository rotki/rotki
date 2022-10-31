import isEqual from 'lodash/isEqual';
import { Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { api } from '@/services/rotkehlchen-api';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useAssociatedLocationsStore } from '@/store/history/associated-locations';
import { AssetMovementEntry } from '@/store/history/types';
import {
  defaultHistoricPayloadState,
  mapCollectionEntriesWithMeta
} from '@/store/history/utils';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { Collection, CollectionResponse } from '@/types/collection';
import { SupportedExchange } from '@/types/exchanges';
import { EntryWithMeta } from '@/types/history/meta';
import {
  AssetMovement,
  AssetMovementCollectionResponse,
  AssetMovementRequestPayload
} from '@/types/history/movements';
import { TradeLocation } from '@/types/history/trade-location';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { useTradeLocations } from '@/types/trades';
import {
  defaultCollectionState,
  mapCollectionResponse
} from '@/utils/collection';
import { logger } from '@/utils/logging';

export const useAssetMovements = defineStore('history/assetMovements', () => {
  const assetMovements = ref(
    defaultCollectionState<AssetMovementEntry>()
  ) as Ref<Collection<AssetMovementEntry>>;

  const assetMovementsPayload: Ref<Partial<AssetMovementRequestPayload>> = ref(
    defaultHistoricPayloadState<AssetMovement>()
  );

  const locationsStore = useAssociatedLocationsStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { fetchAssociatedLocations } = locationsStore;
  const { exchangeName } = useTradeLocations();
  const { tc } = useI18n();

  const fetchAssetMovements = async (
    refresh: boolean = false,
    onlyLocation?: SupportedExchange
  ) => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
      Section.ASSET_MOVEMENT,
      !!onlyLocation
    );
    const taskType = TaskType.MOVEMENTS;

    const fetchAssetMovementsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<AssetMovementRequestPayload>
    ) => {
      const defaults: AssetMovementRequestPayload = {
        limit: 0,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
        onlyCache
      };

      const payload: AssetMovementRequestPayload = Object.assign(
        defaults,
        parameters ?? get(assetMovementsPayload)
      );

      const { fetchEnsNames } = useEthNamesStore();
      if (onlyCache) {
        const result = await api.history.assetMovements(payload);
        const mapped = mapCollectionEntriesWithMeta<AssetMovement>(
          mapCollectionResponse(result)
        ) as Collection<AssetMovementEntry>;

        const addresses: string[] = [];
        result.entries.forEach(item => {
          if (item.entry.address) {
            addresses.push(item.entry.address);
          }
        });

        await fetchEnsNames(addresses, false);

        return mapped;
      }

      const { taskId } = await api.history.assetMovementsTask(payload);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : tc('actions.asset_movements.all_exchanges');
      const taskMeta = {
        title: tc('actions.asset_movements.task.title'),
        description: tc('actions.asset_movements.task.description', undefined, {
          exchange
        }),
        location,
        numericKeys: []
      };

      const { result } = await awaitTask<
        CollectionResponse<EntryWithMeta<AssetMovement>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = AssetMovementCollectionResponse.parse(result);
      const mapped = mapCollectionEntriesWithMeta<AssetMovement>(
        mapCollectionResponse(parsedResult)
      ) as Collection<AssetMovementEntry>;

      const addresses: string[] = [];
      result.entries.forEach(item => {
        if (item.entry.address) {
          addresses.push(item.entry.address);
        }
      });

      await fetchEnsNames(addresses, false);

      return mapped;
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
        set(assetMovements, await fetchAssetMovementsHandler(true));
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
            await fetchAssetMovementsHandler(false, {
              location
            }).catch(error => {
              notify({
                title: tc('actions.asset_movements.error.title', undefined, {
                  exchange
                }),
                message: tc(
                  'actions.asset_movements.error.description',
                  undefined,
                  {
                    exchange,
                    error
                  }
                ),
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

  const updateAssetMovementsPayload = async (
    newPayload: Partial<AssetMovementRequestPayload>
  ) => {
    if (!isEqual(get(assetMovementsPayload), newPayload)) {
      set(assetMovementsPayload, newPayload);
      await fetchAssetMovements();
    }
  };

  const reset = () => {
    set(assetMovements, defaultCollectionState<AssetMovementEntry>());
    set(assetMovementsPayload, defaultHistoricPayloadState<AssetMovement>());
  };

  return {
    assetMovements,
    assetMovementsPayload,
    updateAssetMovementsPayload,
    fetchAssetMovements,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssetMovements, import.meta.hot));
}
