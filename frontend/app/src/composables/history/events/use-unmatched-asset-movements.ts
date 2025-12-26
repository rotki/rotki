import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { HistoryEventCollectionRow } from '@/types/history/events/schemas';
import { Severity } from '@rotki/common';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useNotificationsStore } from '@/store/notifications';
import { logger } from '@/utils/logging';

export interface UnmatchedAssetMovement {
  groupIdentifier: string;
  events: HistoryEventCollectionRow;
}

interface UseUnmatchedAssetMovementsReturn {
  unmatchedMovements: Ref<UnmatchedAssetMovement[]>;
  unmatchedCount: ComputedRef<number>;
  loading: Ref<boolean>;
  fetchUnmatchedAssetMovements: () => Promise<void>;
  matchAssetMovement: (assetMovementId: number, matchedEventId: number) => Promise<ActionStatus>;
  refreshAfterMatch: () => Promise<void>;
}

const unmatchedMovements = ref<UnmatchedAssetMovement[]>([]);
const loading = ref<boolean>(false);

export function useUnmatchedAssetMovements(): UseUnmatchedAssetMovementsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();

  const {
    fetchHistoryEvents,
    getUnmatchedAssetMovements,
    matchAssetMovements: matchAssetMovementsApi,
  } = useHistoryEventsApi();

  const unmatchedCount = computed<number>(() => get(unmatchedMovements).length);

  const fetchUnmatchedAssetMovements = async (): Promise<void> => {
    set(loading, true);
    try {
      const groupIdentifiers = await getUnmatchedAssetMovements();

      if (groupIdentifiers.length === 0) {
        set(unmatchedMovements, []);
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

      const movements: UnmatchedAssetMovement[] = [];

      for (const groupId of groupIdentifiers) {
        const eventsForGroup = response.entries.filter((row) => {
          const events = Array.isArray(row) ? row : [row];
          return events.some(event => event.entry.groupIdentifier === groupId);
        });

        if (eventsForGroup.length > 0) {
          movements.push({
            events: eventsForGroup[0],
            groupIdentifier: groupId,
          });
        }
      }

      set(unmatchedMovements, movements);
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
      set(loading, false);
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
    loading,
    matchAssetMovement,
    refreshAfterMatch,
    unmatchedCount,
    unmatchedMovements,
  };
}
