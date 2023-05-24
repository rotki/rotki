import { type MaybeRef } from '@vueuse/core';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { type SupportedExchange } from '@/types/exchanges';
import { type EntryWithMeta } from '@/types/history/meta';
import {
  type AssetMovement,
  type AssetMovementEntry,
  type AssetMovementRequestPayload
} from '@/types/history/asset-movements';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type TradeLocation } from '@/types/history/trade/location';

export const useAssetMovements = () => {
  const locationsStore = useHistoryStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { fetchAssociatedLocations } = locationsStore;
  const { exchangeName } = useLocations();
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const { getAssetMovements, getAssetMovementsTask } = useAssetMovementsApi();

  const syncAssetMovementsTask = async (
    location: TradeLocation
  ): Promise<boolean> => {
    const taskType = TaskType.MOVEMENTS;

    const defaults: AssetMovementRequestPayload = {
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false,
      location
    };

    const { taskId } = await getAssetMovementsTask(defaults);
    const exchange = exchangeName(location);
    const taskMeta = {
      title: t('actions.asset_movements.task.title'),
      description: t('actions.asset_movements.task.description', {
        exchange
      }),
      location
    };

    try {
      await awaitTask<
        CollectionResponse<EntryWithMeta<AssetMovement>>,
        TaskMeta
      >(taskId, taskType, taskMeta, true);
    } catch (e: any) {
      notify({
        title: t('actions.asset_movements.error.title', {
          exchange
        }),
        message: t('actions.asset_movements.error.description', {
          exchange,
          error: e.message
        }),
        display: true
      });
    }

    return false;
  };

  const refreshAssetMovements = async (
    userInitiated = false,
    location?: SupportedExchange
  ): Promise<void> => {
    const { setStatus, isFirstLoad, resetStatus, fetchDisabled } =
      useStatusUpdater(Section.ASSET_MOVEMENT);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping asset movement refresh');
      return;
    }

    await fetchAssociatedLocations();
    const locations = location ? [location] : get(associatedLocations);

    try {
      setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
      await Promise.all(locations.map(syncAssetMovementsTask));
      await fetchAssociatedLocations();
      setStatus(Status.LOADED);
    } catch (e: any) {
      logger.error(e);
      resetStatus();
    }
  };

  const fetchAssetMovements = async (
    payload: MaybeRef<AssetMovementRequestPayload>
  ): Promise<Collection<AssetMovementEntry>> => {
    const result = await getAssetMovements({
      ...get(payload),
      onlyCache: true
    });
    return mapCollectionEntriesWithMeta<AssetMovement>(
      mapCollectionResponse(result)
    );
  };

  return {
    refreshAssetMovements,
    fetchAssetMovements
  };
};
