import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { HistoryEventCollectionRow } from '@/types/history/events/schemas';
import type { TaskMeta } from '@/types/task';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useTaskApi } from '@/composables/api/task';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

interface RawUnmatchedAssetMovement {
  groupIdentifier: string;
  events: HistoryEventCollectionRow;
  asset: string;
}

export interface UnmatchedAssetMovement extends RawUnmatchedAssetMovement {
  isFiat: boolean;
}

interface UseUnmatchedAssetMovementsReturn {
  unmatchedMovements: ComputedRef<UnmatchedAssetMovement[]>;
  ignoredMovements: ComputedRef<UnmatchedAssetMovement[]>;
  unmatchedCount: ComputedRef<number>;
  ignoredCount: ComputedRef<number>;
  loading: Ref<boolean>;
  ignoredLoading: Ref<boolean>;
  autoMatchLoading: ComputedRef<boolean>;
  fetchUnmatchedAssetMovements: (onlyIgnored?: boolean) => Promise<void>;
  matchAssetMovement: (assetMovementId: number, matchedEventId: number) => Promise<ActionStatus>;
  refreshUnmatchedAssetMovements: (skipIgnored?: boolean) => Promise<void>;
  triggerAutoMatch: () => Promise<void>;
}

const rawUnmatchedMovements = ref<RawUnmatchedAssetMovement[]>([]);
const rawIgnoredMovements = ref<RawUnmatchedAssetMovement[]>([]);
const loading = ref<boolean>(false);
const ignoredLoading = ref<boolean>(false);

export const useUnmatchedAssetMovements = createSharedComposable((): UseUnmatchedAssetMovementsReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();
  const { assetInfo } = useAssetInfoRetrieval();
  const { triggerTask } = useTaskApi();
  const { awaitTask, useIsTaskRunning } = useTaskStore();

  const {
    fetchHistoryEvents,
    getUnmatchedAssetMovements,
    matchAssetMovements: matchAssetMovementsApi,
  } = useHistoryEventsApi();

  const autoMatchLoading = useIsTaskRunning(TaskType.MATCH_ASSET_MOVEMENTS);

  function addIsFiat(movements: RawUnmatchedAssetMovement[]): UnmatchedAssetMovement[] {
    return movements.map(movement => ({
      ...movement,
      isFiat: get(assetInfo(movement.asset))?.assetType === 'fiat',
    }));
  }

  const unmatchedMovements = computed<UnmatchedAssetMovement[]>(() => addIsFiat(get(rawUnmatchedMovements)));
  const ignoredMovements = computed<UnmatchedAssetMovement[]>(() => addIsFiat(get(rawIgnoredMovements)));

  const unmatchedCount = computed<number>(() => get(unmatchedMovements).length);
  const ignoredCount = computed<number>(() => get(ignoredMovements).length);

  const fetchUnmatchedAssetMovements = async (onlyIgnored?: boolean): Promise<void> => {
    const isIgnored = onlyIgnored === true;
    const loadingRef = isIgnored ? ignoredLoading : loading;
    const movementsRef = isIgnored ? rawIgnoredMovements : rawUnmatchedMovements;

    set(loadingRef, true);
    try {
      const groupIdentifiers = await getUnmatchedAssetMovements(onlyIgnored);

      if (groupIdentifiers.length === 0) {
        set(movementsRef, []);
        return;
      }

      const response = await fetchHistoryEvents({
        aggregateByGroupIds: false,
        groupIdentifiers,
        limit: -1,
        offset: 0,
        orderByAttributes: ['timestamp'],
        ascending: [false],
      });

      const movements: RawUnmatchedAssetMovement[] = [];

      for (const groupId of groupIdentifiers) {
        const eventsForGroup = response.entries.filter((row) => {
          const events = Array.isArray(row) ? row : [row];
          return events.some(event => event.entry.groupIdentifier === groupId);
        });

        if (eventsForGroup.length > 0) {
          const eventRow = eventsForGroup[0];
          const events = Array.isArray(eventRow) ? eventRow : [eventRow];
          const asset = events[0]?.entry.asset ?? '';

          movements.push({
            asset,
            events: eventRow,
            groupIdentifier: groupId,
          });
        }
      }

      set(movementsRef, movements);
    }
    catch (error: any) {
      logger.error('Failed to fetch unmatched asset movements:', error);
      setMessage({
        description: t('actions.asset_movement_matching.fetch_error.description', { error: error.message }),
        title: t('actions.asset_movement_matching.fetch_error.title'),
      });
    }
    finally {
      set(loadingRef, false);
    }
  };

  const matchAssetMovement = async (
    assetMovementId: number,
    matchedEventId: number,
  ): Promise<ActionStatus> => {
    try {
      const success = await matchAssetMovementsApi(assetMovementId, matchedEventId);

      if (success) {
        setMessage({
          description: t('actions.asset_movement_matching.success.description'),
          title: t('actions.asset_movement_matching.success.title'),
          success: true,
        });
      }

      return { message: '', success };
    }
    catch (error: any) {
      logger.error('Failed to match asset movement:', error);
      setMessage({
        description: t('actions.asset_movement_matching.error.description', { error: error.message }),
        title: t('actions.asset_movement_matching.error.title'),
      });
      return { message: error.message, success: false };
    }
  };

  const refreshUnmatchedAssetMovements = async (skipIgnored = false): Promise<void> => {
    await fetchUnmatchedAssetMovements();
    if (!skipIgnored) {
      await fetchUnmatchedAssetMovements(true);
    }
  };

  const triggerAutoMatch = async (): Promise<void> => {
    try {
      const { taskId } = await triggerTask('asset_movement_matching');

      await awaitTask<boolean, TaskMeta>(
        taskId,
        TaskType.MATCH_ASSET_MOVEMENTS,
        {
          title: t('asset_movement_matching.auto_match.task_title'),
        },
      );

      await refreshUnmatchedAssetMovements(true);
    }
    catch (error: any) {
      logger.error('Failed to trigger auto match:', error);
      setMessage({
        description: t('asset_movement_matching.auto_match.error', { error: error.message }),
        title: t('asset_movement_matching.auto_match.error_title'),
      });
    }
  };

  return {
    autoMatchLoading,
    fetchUnmatchedAssetMovements,
    ignoredCount,
    ignoredLoading,
    ignoredMovements,
    loading,
    matchAssetMovement,
    refreshUnmatchedAssetMovements,
    triggerAutoMatch,
    unmatchedCount,
    unmatchedMovements,
  };
});
