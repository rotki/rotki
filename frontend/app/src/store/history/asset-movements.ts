import isEqual from 'lodash/isEqual';
import { type Ref } from 'vue';
import { useAssetMovementsApi } from '@/services/history/asset-movements';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useAssociatedLocationsStore } from '@/store/history/associated-locations';
import { useNotificationsStore } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type SupportedExchange } from '@/types/exchanges';
import { type EntryWithMeta } from '@/types/history/meta';
import {
  type AssetMovement,
  AssetMovementCollectionResponse,
  type AssetMovementEntry,
  type AssetMovementRequestPayload
} from '@/types/history/movements';
import { type TradeLocation } from '@/types/history/trade-location';
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

export const useAssetMovements = defineStore('history/assetMovements', () => {
  const assetMovements: Ref<Collection<AssetMovementEntry>> = ref(
    defaultCollectionState<AssetMovementEntry>()
  );

  const assetMovementsPayload: Ref<Partial<AssetMovementRequestPayload>> = ref(
    defaultHistoricPayloadState<AssetMovement>()
  );

  const locationsStore = useAssociatedLocationsStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { fetchAssociatedLocations } = locationsStore;
  const { exchangeName } = useTradeLocations();
  const { tc } = useI18n();
  const { notify } = useNotificationsStore();

  const { getAssetMovements, getAssetMovementsTask } = useAssetMovementsApi();

  const fetchAssetMovements = async (
    refresh = false,
    onlyLocation?: SupportedExchange
  ): Promise<void> => {
    const { awaitTask, isTaskRunning } = useTasks();
    const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
      Section.ASSET_MOVEMENT,
      !!onlyLocation
    );
    const taskType = TaskType.MOVEMENTS;

    const fetchAssetMovementsHandler = async (
      onlyCache: boolean,
      parameters?: Partial<AssetMovementRequestPayload>
    ): Promise<Collection<AssetMovementEntry>> => {
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

      const { fetchEnsNames } = useAddressesNamesStore();
      if (onlyCache) {
        const result = await getAssetMovements(payload);
        const mapped: Collection<AssetMovementEntry> =
          mapCollectionEntriesWithMeta<AssetMovement>(
            mapCollectionResponse(result)
          );

        const addresses: string[] = [];
        result.entries.forEach(item => {
          if (item.entry.address) {
            addresses.push(item.entry.address);
          }
        });

        await fetchEnsNames(addresses);

        return mapped;
      }

      const { taskId } = await getAssetMovementsTask(payload);
      const location = parameters?.location ?? '';
      const exchange = location
        ? exchangeName(location as TradeLocation)
        : tc('actions.asset_movements.all_exchanges');
      const taskMeta = {
        title: tc('actions.asset_movements.task.title'),
        description: tc('actions.asset_movements.task.description', undefined, {
          exchange
        }),
        location
      };

      const { result } = await awaitTask<
        CollectionResponse<EntryWithMeta<AssetMovement>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);

      setStatus(
        get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
      );

      const parsedResult = AssetMovementCollectionResponse.parse(result);
      const mapped: Collection<AssetMovementEntry> =
        mapCollectionEntriesWithMeta<AssetMovement>(
          mapCollectionResponse(parsedResult)
        );

      const addresses: string[] = [];
      result.entries.forEach(item => {
        if (item.entry.address) {
          addresses.push(item.entry.address);
        }
      });

      await fetchEnsNames(addresses);

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

      const fetchOnlyCache = async (): Promise<void> => {
        set(assetMovements, await fetchAssetMovementsHandler(true));
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
  ): Promise<void> => {
    if (!isEqual(get(assetMovementsPayload), newPayload)) {
      set(assetMovementsPayload, newPayload);
      await fetchAssetMovements();
    }
  };

  return {
    assetMovements,
    assetMovementsPayload,
    updateAssetMovementsPayload,
    fetchAssetMovements
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssetMovements, import.meta.hot));
}
