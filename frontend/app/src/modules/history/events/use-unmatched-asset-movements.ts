import type { LinkedMovementMatch } from '@/modules/history/events/event-payloads';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { HistoryEventCollectionRow } from '@/modules/history/events/schemas';
import { createSharedComposable } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type Ref, ref, shallowReadonly } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { type ActionStatus, actionStatusOf } from '@/modules/core/common/action';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import { useAssetMovementMatchingApi } from '@/modules/history/api/events/use-asset-movement-matching-api';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { assetMovementMatchActivity } from './history-events.activity';
import { createUnmatchedLists, useAutoMatchingTask } from './use-unmatched-matching';

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
  /** Why the last fetch of the unmatched movements failed, kept until a load succeeds. */
  unmatchedError: Readonly<Ref<unknown>>;
  /** Why the last fetch of the ignored movements failed, kept until a load succeeds. */
  ignoredError: Readonly<Ref<unknown>>;
  autoMatchLoading: ComputedRef<boolean>;
  autoMatchMinimumTier: Readonly<Ref<string | null>>;
  isAutoMatchAllowed: Readonly<Ref<boolean>>;
  autoMatchMovement: (linkedMovement: LinkedMovementMatch) => Promise<boolean>;
  fetchUnmatchedAssetMovements: (onlyIgnored?: boolean) => Promise<void>;
  matchAssetMovement: (assetMovementId: number, matchedEventIds: number[]) => Promise<ActionStatus<unknown>>;
  resolveExternal: (assetMovementId: number) => Promise<ActionStatus<unknown>>;
  refreshUnmatchedAssetMovements: (skipIgnored?: boolean) => Promise<void>;
  triggerAssetMovementAutoMatching: () => Promise<void>;
}

const {
  ignored: rawIgnoredMovements,
  ignoredError,
  ignoredLoading,
  load,
  loading,
  unmatched: rawUnmatchedMovements,
  unmatchedError,
} = createUnmatchedLists<UnmatchedEventGroup>();
const triggerAutoMatchLoading = ref<boolean>(false);

/**
 * One group per identifier that has events, in the order the backend listed the identifiers, named
 * by the asset of its first event. An identifier with no events left is dropped.
 */
function groupMovements(groupIdentifiers: string[], rows: HistoryEventCollectionRow[]): UnmatchedEventGroup[] {
  const movements: UnmatchedEventGroup[] = [];
  for (const groupIdentifier of groupIdentifiers) {
    const row = rows.find(candidate => arrayify(candidate).some(event => event.entry.groupIdentifier === groupIdentifier));
    if (row)
      movements.push({ asset: arrayify(row)[0]?.entry.asset ?? '', events: row, groupIdentifier });
  }
  return movements;
}

export const useUnmatchedAssetMovements = createSharedComposable((): UseUnmatchedAssetMovementsReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { getAssetInfo } = useAssetInfoRetrieval();

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const {
    getAssetMovementMatches,
    getUnmatchedAssetMovements,
    matchAssetMovements: matchAssetMovementsApi,
    triggerAssetMovementMatching,
  } = useAssetMovementMatchingApi();
  const { signalEventsModified } = useHistoryStore();
  const { allowed: isAssetMovementMatchingAllowed, minimumTier: assetMovementMatchingMinimumTier } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

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

  /**
   * Loads the unmatched, or with `onlyIgnored` the ignored, movements.
   *
   * @remarks
   * A websocket message triggers this in the background as well, so a failure is kept for the list
   * to show rather than interrupting the user with a dialog. The rows of the last good load stay,
   * since the action center counts them, and the failure is kept until a load succeeds.
   */
  const fetchUnmatchedAssetMovements = async (onlyIgnored?: boolean): Promise<void> => load(onlyIgnored, async (): Promise<UnmatchedEventGroup[]> => {
    const groupIdentifiers = await getUnmatchedAssetMovements(onlyIgnored);

    if (groupIdentifiers.length === 0)
      return [];

    const response = await fetchHistoryEvents({
      aggregateByGroupIds: false,
      groupIdentifiers,
      limit: -1,
      offset: 0,
      orderByAttributes: ['timestamp'],
      ascending: [false],
    });

    return groupMovements(groupIdentifiers, response.entries);
  }, 'Failed to fetch unmatched asset movements:');

  const matchAssetMovement = async (
    assetMovementId: number,
    matchedEventIds: number[],
  ): Promise<ActionStatus<unknown>> => {
    try {
      const success = await matchAssetMovementsApi(assetMovementId, matchedEventIds);

      if (success)
        signalEventsModified();

      return actionStatusOf(success, t('common.change_not_applied'));
    }
    catch (error: unknown) {
      logger.error('Failed to match asset movement:', error);
      return { message: error, success: false };
    }
  };

  /**
   * Resolves a movement as moving to or from an untracked address.
   *
   * @remarks
   * Reports nothing itself: a failure carries the thrown error back for the panel to name, and the
   * caller surfaces a success with an undo affordance.
   *
   * @param assetMovementId - identifier of the movement's own event
   */
  const resolveExternal = async (assetMovementId: number): Promise<ActionStatus<unknown>> => {
    try {
      const success = await matchAssetMovementsApi(assetMovementId, undefined, true);

      if (success)
        signalEventsModified();

      return actionStatusOf(success, t('common.change_not_applied'));
    }
    catch (error: unknown) {
      logger.error('Failed to resolve asset movement as external:', error);
      return { message: error, success: false };
    }
  };

  const refreshUnmatchedAssetMovements = async (skipIgnored = false): Promise<void> => {
    await fetchUnmatchedAssetMovements();
    if (!skipIgnored) {
      await fetchUnmatchedAssetMovements(true);
    }
  };

  const { autoMatchLoading, triggerAutoMatching: triggerAssetMovementAutoMatching } = useAutoMatchingTask({
    activity: assetMovementMatchActivity,
    allowed: isAssetMovementMatchingAllowed,
    failureLog: 'Failed to trigger auto match:',
    loading: triggerAutoMatchLoading,
    onMatched: async (): Promise<void> => refreshUnmatchedAssetMovements(true),
    trigger: triggerAssetMovementMatching,
  });

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
    ignoredError: shallowReadonly(ignoredError),
    ignoredLoading,
    ignoredMovements,
    loading,
    matchAssetMovement,
    refreshUnmatchedAssetMovements,
    resolveExternal,
    triggerAssetMovementAutoMatching,
    unmatchedCount,
    unmatchedError: shallowReadonly(unmatchedError),
    unmatchedMovements,
  };
});
