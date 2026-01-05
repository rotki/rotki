import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { HistoryEventCollectionRow } from '@/types/history/events/schemas';
import { Severity } from '@rotki/common';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useNotificationsStore } from '@/store/notifications';
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
  fetchUnmatchedAssetMovements: (onlyIgnored?: boolean) => Promise<void>;
  matchAssetMovement: (assetMovementId: number, matchedEventId: number) => Promise<ActionStatus>;
  refreshAfterMatch: () => Promise<void>;
}

const rawUnmatchedMovements = ref<RawUnmatchedAssetMovement[]>([]);
const rawIgnoredMovements = ref<RawUnmatchedAssetMovement[]>([]);
const loading = ref<boolean>(false);
const ignoredLoading = ref<boolean>(false);

export const useUnmatchedAssetMovements = createSharedComposable((): UseUnmatchedAssetMovementsReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const { assetInfo } = useAssetInfoRetrieval();

  const {
    fetchHistoryEvents,
    getUnmatchedAssetMovements,
    matchAssetMovements: matchAssetMovementsApi,
  } = useHistoryEventsApi();

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
      notify({
        display: true,
        message: t('actions.asset_movement_matching.fetch_error.description', { error: error.message }),
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
        notify({
          display: true,
          severity: Severity.INFO,
          message: t('actions.asset_movement_matching.success.description'),
          title: t('actions.asset_movement_matching.success.title'),
        });
      }

      return { message: '', success };
    }
    catch (error: any) {
      logger.error('Failed to match asset movement:', error);
      notify({
        display: true,
        message: t('actions.asset_movement_matching.error.description', { error: error.message }),
        title: t('actions.asset_movement_matching.error.title'),
      });
      return { message: error.message, success: false };
    }
  };

  const refreshAfterMatch = async (): Promise<void> => {
    await fetchUnmatchedAssetMovements();
  };

  return {
    fetchUnmatchedAssetMovements,
    ignoredCount,
    ignoredLoading,
    ignoredMovements,
    loading,
    matchAssetMovement,
    refreshAfterMatch,
    unmatchedCount,
    unmatchedMovements,
  };
});
