import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { mapCollectionResponse } from '@/utils/collection';
import { mapCollectionEntriesWithMeta } from '@/utils/history';
import { logger } from '@/utils/logging';
import { isTaskCancelled } from '@/utils';
import { useTaskStore } from '@/store/tasks';
import { useNotificationsStore } from '@/store/notifications';
import { useHistoryStore } from '@/store/history';
import type { MaybeRef } from '@vueuse/core';
import type { Collection, CollectionResponse } from '@/types/collection';
import type { EntryWithMeta } from '@/types/history/meta';
import type { AssetMovement, AssetMovementEntry, AssetMovementRequestPayload } from '@/types/history/asset-movements';
import type { TaskMeta } from '@/types/task';

interface UseAssetMovementsReturn {
  refreshAssetMovements: (userInitiated?: boolean, location?: string) => Promise<void>;
  fetchAssetMovements: (payload: MaybeRef<AssetMovementRequestPayload>) => Promise<Collection<AssetMovementEntry>>;
}

export function useAssetMovements(): UseAssetMovementsReturn {
  const locationsStore = useHistoryStore();
  const { associatedLocations } = storeToRefs(locationsStore);
  const { fetchAssociatedLocations } = locationsStore;
  const { exchangeName } = useLocations();
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const { getAssetMovements, getAssetMovementsTask } = useAssetMovementsApi();

  const syncAssetMovementsTask = async (location: string): Promise<boolean> => {
    const taskType = TaskType.MOVEMENTS;

    const defaults: AssetMovementRequestPayload = {
      ascending: [false],
      limit: 0,
      location,
      offset: 0,
      onlyCache: false,
      orderByAttributes: ['timestamp'],
    };

    const { taskId } = await getAssetMovementsTask(defaults);
    const exchange = exchangeName(location);
    const taskMeta = {
      description: t('actions.asset_movements.task.description', {
        exchange,
      }),
      location,
      title: t('actions.asset_movements.task.title'),
    };

    try {
      await awaitTask<CollectionResponse<EntryWithMeta<AssetMovement>>, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.asset_movements.error.description', {
            error: error.message,
            exchange,
          }),
          title: t('actions.asset_movements.error.title', {
            exchange,
          }),
        });
      }
    }

    return false;
  };

  const refreshAssetMovements = async (userInitiated = false, location?: string): Promise<void> => {
    const { fetchDisabled, isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.ASSET_MOVEMENT);

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
    }
    catch (error: any) {
      logger.error(error);
      resetStatus();
    }
  };

  const fetchAssetMovements = async (
    payload: MaybeRef<AssetMovementRequestPayload>,
  ): Promise<Collection<AssetMovementEntry>> => {
    const result = await getAssetMovements({
      ...get(payload),
      onlyCache: true,
    });
    return mapCollectionEntriesWithMeta<AssetMovement>(mapCollectionResponse(result));
  };

  return {
    fetchAssetMovements,
    refreshAssetMovements,
  };
}
