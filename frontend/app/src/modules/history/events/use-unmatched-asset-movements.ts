import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { LinkedMovementMatch } from '@/modules/history/events/event-payloads';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import { NotificationGroup } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useAssetMovementMatchingApi } from '@/modules/history/api/events/use-asset-movement-matching-api';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

export interface UnmatchedAssetMovement extends UnmatchedEventGroup {
  isFiat: boolean;
}

export type { PotentialMatchRow } from '@/modules/history/events/matching/types';

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
  resolveExternal: (assetMovementId: number) => Promise<ActionStatus>;
  refreshUnmatchedAssetMovements: (skipIgnored?: boolean) => Promise<void>;
  triggerAssetMovementAutoMatching: () => Promise<void>;
}

const rawUnmatchedMovements = ref<UnmatchedEventGroup[]>([]);
const rawIgnoredMovements = ref<UnmatchedEventGroup[]>([]);
const loading = ref<boolean>(false);
const ignoredLoading = ref<boolean>(false);
const triggerAutoMatchLoading = ref<boolean>(false);

export const useUnmatchedAssetMovements = createSharedComposable((): UseUnmatchedAssetMovementsReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { removeMatching, showErrorMessage, showSuccessMessage } = useNotifications();
  const { getAssetInfo } = useAssetInfoRetrieval();
  const { statusOf, submitTask } = useNativeTask();
  const { useIsActive } = useTaskCenter();

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const {
    getAssetMovementMatches,
    getUnmatchedAssetMovements,
    matchAssetMovements: matchAssetMovementsApi,
    triggerAssetMovementMatching,
  } = useAssetMovementMatchingApi();
  const { signalEventsModified } = useHistoryStore();
  const { allowed: isAssetMovementMatchingAllowed, minimumTier: assetMovementMatchingMinimumTier } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

  const autoMatchLoading = logicOr(triggerAutoMatchLoading, useIsActive(ActivityKind.HISTORY_EVENTS, ActivityPart.MATCH));

  function addIsFiat(movements: UnmatchedEventGroup[]): UnmatchedAssetMovement[] {
    return movements.map(movement => ({
      ...movement,
      isFiat: getAssetInfo(movement.asset)?.assetType === 'fiat',
    }));
  }

  const unmatchedMovements = computed<UnmatchedAssetMovement[]>(() => addIsFiat(get(rawUnmatchedMovements)));
  const ignoredMovements = computed<UnmatchedAssetMovement[]>(() => addIsFiat(get(rawIgnoredMovements)));

  const unmatchedCount = computed<number>(() => get(unmatchedMovements).length);
  const ignoredCount = computed<number>(() => get(ignoredMovements).length);

  function clearUnmatchedAssetMovementsNotification(): void {
    removeMatching(notification => notification.group === NotificationGroup.UNMATCHED_ASSET_MOVEMENTS);
  }

  const fetchUnmatchedAssetMovements = async (onlyIgnored?: boolean): Promise<void> => {
    const isIgnored = onlyIgnored === true;
    const loadingRef = isIgnored ? ignoredLoading : loading;
    const movementsRef = isIgnored ? rawIgnoredMovements : rawUnmatchedMovements;

    set(loadingRef, true);
    try {
      const groupIdentifiers = await getUnmatchedAssetMovements(onlyIgnored);

      if (groupIdentifiers.length === 0) {
        set(movementsRef, []);
        if (!isIgnored)
          clearUnmatchedAssetMovementsNotification();
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

      const movements: UnmatchedEventGroup[] = [];

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

  /**
   * Resolves a movement as moving to or from an untracked address.
   *
   * @remarks
   * Reports failure through the shared error dialog, but stays silent on success: the caller
   * surfaces the outcome with an undo affordance instead.
   *
   * @param assetMovementId - identifier of the movement's own event
   */
  const resolveExternal = async (assetMovementId: number): Promise<ActionStatus> => {
    try {
      const success = await matchAssetMovementsApi(assetMovementId, undefined, true);

      if (success)
        signalEventsModified();

      return { message: '', success };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to resolve asset movement as external:', error);
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
    if (!get(isAssetMovementMatchingAllowed) || statusOf(ActivityKind.HISTORY_EVENTS, ActivityPart.MATCH).active)
      return;

    set(triggerAutoMatchLoading, true);

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.HISTORY_EVENTS, ActivityPart.MATCH),
      kind: ActivityKind.HISTORY_EVENTS,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => triggerAssetMovementMatching(),
        ),
        () => {},
      ),
      subtitle: activityLabel(ActivityKind.HISTORY_EVENTS, ActivityPart.MATCH),
      title: t('task_center.group.history_events'),
    });

    if (!isErr(outcome)) {
      await refreshUnmatchedAssetMovements(true);
      signalEventsModified();
    }
    else if (isActionable(outcome.error)) {
      logger.error('Failed to trigger auto match:', outcome.error);
      showErrorMessage(t('asset_movement_matching.auto_match.error_title'), t('asset_movement_matching.auto_match.error', { error: outcome.error.message }));
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
    resolveExternal,
    triggerAssetMovementAutoMatching,
    unmatchedCount,
    unmatchedMovements,
  };
});
