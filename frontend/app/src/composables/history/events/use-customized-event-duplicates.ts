import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { Collection } from '@/types/collection';
import type { HistoryEventCollectionRow, HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { type CustomizedEventDuplicates, useCustomizedEventDuplicatesApi } from '@/composables/api/history/events/customized-event-duplicates';
import { useMessageStore } from '@/store/message';
import { arrayify } from '@/utils/array';
import { logger } from '@/utils/logging';

export interface CustomizedEventDuplicate {
  groupIdentifier: string;
  events: HistoryEventCollectionRow;
}

export interface DuplicateRow {
  groupIdentifier: string;
  txHash: string;
  location: string;
  timestamp: number;
  original: CustomizedEventDuplicate;
}

export interface FetchDuplicateEventsPayload {
  groupIds: string[];
  limit: number;
  offset: number;
}

interface UseCustomizedEventDuplicatesReturn {
  autoFixGroupIds: ComputedRef<string[]>;
  manualReviewGroupIds: ComputedRef<string[]>;
  autoFixCount: ComputedRef<number>;
  manualReviewCount: ComputedRef<number>;
  totalCount: ComputedRef<number>;
  loading: Ref<boolean>;
  fixLoading: Ref<boolean>;
  fetchCustomizedEventDuplicates: () => Promise<void>;
  fetchDuplicateEvents: (payload: FetchDuplicateEventsPayload) => Promise<Collection<DuplicateRow>>;
  fixDuplicates: (groupIdentifiers?: string[]) => Promise<ActionStatus>;
}

function getEventEntry(row: HistoryEventCollectionRow): HistoryEventEntryWithMeta {
  return Array.isArray(row) ? row[0] : row;
}

function mapToDuplicateRow(groupId: string, events: HistoryEventCollectionRow): DuplicateRow {
  const entry = getEventEntry(events).entry;
  return {
    groupIdentifier: groupId,
    location: entry.location,
    original: { events, groupIdentifier: groupId },
    timestamp: entry.timestamp,
    txHash: 'txRef' in entry ? (entry.txRef ?? '') : '',
  };
}

export const useCustomizedEventDuplicates = createSharedComposable((): UseCustomizedEventDuplicatesReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const { fixCustomizedEventDuplicates, getCustomizedEventDuplicates } = useCustomizedEventDuplicatesApi();

  const rawAutoFixGroupIds = ref<string[]>([]);
  const rawManualReviewGroupIds = ref<string[]>([]);
  const loading = ref<boolean>(false);
  const fixLoading = ref<boolean>(false);

  const autoFixGroupIds = computed<string[]>(() => get(rawAutoFixGroupIds));
  const manualReviewGroupIds = computed<string[]>(() => get(rawManualReviewGroupIds));

  const autoFixCount = computed<number>(() => get(rawAutoFixGroupIds).length);
  const manualReviewCount = computed<number>(() => get(rawManualReviewGroupIds).length);
  const totalCount = computed<number>(() => get(autoFixCount) + get(manualReviewCount));

  const fetchCustomizedEventDuplicates = async (): Promise<void> => {
    set(loading, true);
    try {
      const result: CustomizedEventDuplicates = await getCustomizedEventDuplicates();
      set(rawAutoFixGroupIds, result.autoFixGroupIds);
      set(rawManualReviewGroupIds, result.manualReviewGroupIds);
    }
    catch (error: any) {
      logger.error('Failed to fetch customized event duplicates:', error);
      setMessage({
        description: t('actions.customized_event_duplicates.fetch_error.description', { error: error.message }),
        title: t('actions.customized_event_duplicates.fetch_error.title'),
      });
    }
    finally {
      set(loading, false);
    }
  };

  const fetchDuplicateEvents = async (payload: FetchDuplicateEventsPayload): Promise<Collection<DuplicateRow>> => {
    const { groupIds, limit, offset } = payload;

    if (groupIds.length === 0) {
      return {
        data: [],
        found: 0,
        limit,
        total: 0,
        totalValue: undefined,
      };
    }

    // Get the group IDs for the current page
    const paginatedGroupIds = groupIds.slice(offset, offset + limit);

    if (paginatedGroupIds.length === 0) {
      return {
        data: [],
        found: groupIds.length,
        limit,
        total: groupIds.length,
        totalValue: undefined,
      };
    }

    const response = await fetchHistoryEvents({
      aggregateByGroupIds: false,
      groupIdentifiers: paginatedGroupIds,
      limit: -1,
      offset: 0,
      orderByAttributes: ['timestamp'],
      ascending: [false],
    });

    const rows: DuplicateRow[] = [];
    for (const groupId of paginatedGroupIds) {
      const eventsForGroup = response.entries.filter((row) => {
        const events = arrayify(row);
        return events.some(event => event.entry.groupIdentifier === groupId);
      });

      if (eventsForGroup.length > 0) {
        rows.push(mapToDuplicateRow(groupId, eventsForGroup[0]));
      }
    }

    return {
      data: rows,
      found: groupIds.length,
      limit,
      total: groupIds.length,
      totalValue: undefined,
    };
  };

  const fixDuplicates = async (groupIdentifiers?: string[]): Promise<ActionStatus> => {
    set(fixLoading, true);
    try {
      const result = await fixCustomizedEventDuplicates(groupIdentifiers);

      if (result.removedEventIdentifiers.length > 0) {
        setMessage({
          description: t('actions.customized_event_duplicates.fix_success.description', {
            count: result.removedEventIdentifiers.length,
          }),
          success: true,
          title: t('actions.customized_event_duplicates.fix_success.title'),
        });
      }

      // Refresh the list after fixing
      await fetchCustomizedEventDuplicates();

      return { success: true };
    }
    catch (error: any) {
      logger.error('Failed to fix customized event duplicates:', error);
      setMessage({
        description: t('actions.customized_event_duplicates.fix_error.description', { error: error.message }),
        title: t('actions.customized_event_duplicates.fix_error.title'),
      });
      return { message: error.message, success: false };
    }
    finally {
      set(fixLoading, false);
    }
  };

  return {
    autoFixCount,
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    fixDuplicates,
    fixLoading,
    loading,
    manualReviewCount,
    manualReviewGroupIds,
    totalCount,
  };
});
