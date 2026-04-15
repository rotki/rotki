import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/modules/common/action';
import type { LinkedMovementMatch } from '@/modules/history/events/event-payloads';
import type { HistoryEventCollectionRow, HistoryEventEntry } from '@/modules/history/events/schemas';
import type { TaskMeta } from '@/modules/tasks/types';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useAssetMovementMatchingApi } from '@/composables/api/history/events/asset-movement-matching';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { useHistoryStore } from '@/store/history';
import { arrayify } from '@/utils/array';
import { logger } from '@/utils/logging';

interface RawUnmatchedAssetMovement {
  groupIdentifier: string;
  events: HistoryEventCollectionRow;
  asset: string;
}

export interface UnmatchedAssetMovement extends RawUnmatchedAssetMovement {
  isFiat: boolean;
}

export interface PotentialMatchRow {
  identifier: number;
  entry: HistoryEventEntry;
  isCloseMatch: boolean;
}

interface UseUnmatchedAssetMovementsReturn {
  unmatchedMovements: ComputedRef<UnmatchedAssetMovement[]>;
  ignoredMovements: ComputedRef<UnmatchedAssetMovement[]>;
  unmatchedCount: ComputedRef<number>;
  ignoredCount: ComputedRef<number>;
  loading: Ref<boolean>;
  ignoredLoading: Ref<boolean>;
  autoMatchLoading: ComputedRef<boolean>;
  autoMatchMinimumTier: Readonly<Ref<string | null>>;
  isAutoMatchAllowed: Readonly<Ref<boolean>>;
  autoMatchMovement: (linkedMovement: LinkedMovementMatch) => Promise<boolean>;
  fetchUnmatchedAssetMovements: (onlyIgnored?: boolean) => Promise<void>;
  matchAssetMovement: (assetMovementId: number, matchedEventIds: number[]) => Promise<ActionStatus>;
  refreshUnmatchedAssetMovements: (skipIgnored?: boolean) => Promise<void>;
  triggerAssetMovementAutoMatching: () => Promise<void>;
}

const rawUnmatchedMovements = ref<RawUnmatchedAssetMovement[]>([]);
const rawIgnoredMovements = ref<RawUnmatchedAssetMovement[]>([]);
const loading = ref<boolean>(false);
const ignoredLoading = ref<boolean>(false);
const triggerAutoMatchLoading = ref<boolean>(false);

export const useUnmatchedAssetMovements = createSharedComposable((): UseUnmatchedAssetMovementsReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage, showSuccessMessage } = useNotifications();
  const { getAssetInfo } = useAssetInfoRetrieval();
  const { runTask } = useTaskHandler();
  const { useIsTaskRunning } = useTaskStore();

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const {
    getAssetMovementMatches,
    getUnmatchedAssetMovements,
    matchAssetMovements: matchAssetMovementsApi,
    triggerAssetMovementMatching,
  } = useAssetMovementMatchingApi();
  const { signalEventsModified } = useHistoryStore();
  const { allowed: isAssetMovementMatchingAllowed, minimumTier: assetMovementMatchingMinimumTier } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

  const isTaskRunning = useIsTaskRunning(TaskType.MATCH_ASSET_MOVEMENTS);
  const autoMatchLoading = logicOr(triggerAutoMatchLoading, isTaskRunning);

  function addIsFiat(movements: RawUnmatchedAssetMovement[]): UnmatchedAssetMovement[] {
    return movements.map(movement => ({
      ...movement,
      isFiat: getAssetInfo(movement.asset)?.assetType === 'fiat',
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
          const events = arrayify(row);
          return events.some(event => event.entry.groupIdentifier === groupId);
        });

        if (eventsForGroup.length > 0) {
          const eventRow = eventsForGroup[0];
          const events = arrayify(eventRow);
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
    catch (error: unknown) {
      logger.error('Failed to fetch unmatched asset movements:', error);
      showErrorMessage(t('actions.asset_movement_matching.fetch_error.title'), t('actions.asset_movement_matching.fetch_error.description', { error: getErrorMessage(error) }));
    }
    finally {
      set(loadingRef, false);
    }
  };

  const matchAssetMovement = async (
    assetMovementId: number,
    matchedEventIds: number[],
  ): Promise<ActionStatus> => {
    try {
      const success = await matchAssetMovementsApi(assetMovementId, matchedEventIds);

      if (success) {
        showSuccessMessage(t('actions.asset_movement_matching.success.title'), t('actions.asset_movement_matching.success.description'));
        signalEventsModified();
      }

      return { message: '', success };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to match asset movement:', error);
      showErrorMessage(t('actions.asset_movement_matching.error.title'), t('actions.asset_movement_matching.error.description', { error: message }));
      return { message, success: false };
    }
  };

  const refreshUnmatchedAssetMovements = async (skipIgnored = false): Promise<void> => {
    await fetchUnmatchedAssetMovements();
    if (!skipIgnored) {
      await fetchUnmatchedAssetMovements(true);
    }
  };

  const triggerAssetMovementAutoMatching = async (): Promise<void> => {
    if (!get(isAssetMovementMatchingAllowed) || get(isTaskRunning))
      return;

    set(triggerAutoMatchLoading, true);

    const outcome = await runTask<boolean, TaskMeta>(
      async () => triggerAssetMovementMatching(),
      { type: TaskType.MATCH_ASSET_MOVEMENTS, meta: { title: t('asset_movement_matching.auto_match.task_title') }, guard: false },
    );

    if (outcome.success) {
      await refreshUnmatchedAssetMovements(true);
      signalEventsModified();
    }
    else if (isActionableFailure(outcome)) {
      logger.error('Failed to trigger auto match:', outcome.error);
      showErrorMessage(t('asset_movement_matching.auto_match.error_title'), t('asset_movement_matching.auto_match.error', { error: outcome.message }));
    }

    set(triggerAutoMatchLoading, false);
  };

  async function autoMatchMovement(linkedMovement: LinkedMovementMatch): Promise<boolean> {
    const { groupIdentifier, identifier, timeRange, tolerance } = linkedMovement;
    const suggestions = await getAssetMovementMatches(groupIdentifier, timeRange, false, tolerance);
    if (suggestions.closeMatches.length > 0) {
      await matchAssetMovementsApi(identifier, suggestions.closeMatches);
      return true;
    }
    return false;
  }

  return {
    autoMatchLoading,
    autoMatchMovement,
    autoMatchMinimumTier: assetMovementMatchingMinimumTier,
    fetchUnmatchedAssetMovements,
    isAutoMatchAllowed: isAssetMovementMatchingAllowed,
    ignoredCount,
    ignoredLoading,
    ignoredMovements,
    loading,
    matchAssetMovement,
    refreshUnmatchedAssetMovements,
    triggerAssetMovementAutoMatching,
    unmatchedCount,
    unmatchedMovements,
  };
});
