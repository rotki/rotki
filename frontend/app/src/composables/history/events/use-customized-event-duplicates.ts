import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { HistoryEventCollectionRow } from '@/types/history/events/schemas';
import { type CustomizedEventDuplicates, useHistoryEventsApi } from '@/composables/api/history/events';
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

interface UseCustomizedEventDuplicatesReturn {
  autoFixDuplicates: ComputedRef<CustomizedEventDuplicate[]>;
  autoFixGroupIds: ComputedRef<string[]>;
  manualReviewDuplicates: ComputedRef<CustomizedEventDuplicate[]>;
  manualReviewGroupIds: ComputedRef<string[]>;
  autoFixCount: ComputedRef<number>;
  manualReviewCount: ComputedRef<number>;
  totalCount: ComputedRef<number>;
  loading: Ref<boolean>;
  fixLoading: Ref<boolean>;
  fetchCustomizedEventDuplicates: () => Promise<void>;
  fixDuplicates: (groupIdentifiers?: string[]) => Promise<ActionStatus>;
}

function createDuplicatesComputed(
  groupIds: Ref<string[]>,
  eventsMap: Ref<Map<string, HistoryEventCollectionRow>>,
): ComputedRef<CustomizedEventDuplicate[]> {
  return computed<CustomizedEventDuplicate[]>(() =>
    get(groupIds).map(groupId => ({
      events: get(eventsMap).get(groupId) ?? [],
      groupIdentifier: groupId,
    })).filter((item) => {
      const events = arrayify(item.events);
      return events.length > 0;
    }),
  );
}

const rawAutoFixGroupIds = ref<string[]>([]);
const rawManualReviewGroupIds = ref<string[]>([]);
const autoFixEvents = ref<Map<string, HistoryEventCollectionRow>>(new Map());
const manualReviewEvents = ref<Map<string, HistoryEventCollectionRow>>(new Map());
const loading = ref<boolean>(false);
const fixLoading = ref<boolean>(false);

export const useCustomizedEventDuplicates = createSharedComposable((): UseCustomizedEventDuplicatesReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();

  const {
    fetchHistoryEvents,
    fixCustomizedEventDuplicates,
    getCustomizedEventDuplicates,
  } = useHistoryEventsApi();

  const autoFixDuplicates = createDuplicatesComputed(rawAutoFixGroupIds, autoFixEvents);
  const manualReviewDuplicates = createDuplicatesComputed(rawManualReviewGroupIds, manualReviewEvents);

  const autoFixGroupIds = computed<string[]>(() => get(rawAutoFixGroupIds));
  const manualReviewGroupIds = computed<string[]>(() => get(rawManualReviewGroupIds));

  const autoFixCount = computed<number>(() => get(rawAutoFixGroupIds).length);
  const manualReviewCount = computed<number>(() => get(rawManualReviewGroupIds).length);
  const totalCount = computed<number>(() => get(autoFixCount) + get(manualReviewCount));

  async function fetchEventsForGroupIds(groupIds: string[]): Promise<Map<string, HistoryEventCollectionRow>> {
    if (groupIds.length === 0) {
      return new Map();
    }

    const response = await fetchHistoryEvents({
      aggregateByGroupIds: false,
      groupIdentifiers: groupIds,
      limit: -1,
      offset: 0,
      orderByAttributes: ['timestamp'],
      ascending: [false],
    });

    const eventsMap = new Map<string, HistoryEventCollectionRow>();

    for (const groupId of groupIds) {
      const eventsForGroup = response.entries.filter((row) => {
        const events = arrayify(row);
        return events.some(event => event.entry.groupIdentifier === groupId);
      });

      if (eventsForGroup.length > 0) {
        eventsMap.set(groupId, eventsForGroup[0]);
      }
    }

    return eventsMap;
  }

  const fetchCustomizedEventDuplicates = async (): Promise<void> => {
    set(loading, true);
    try {
      const result: CustomizedEventDuplicates = await getCustomizedEventDuplicates();

      set(rawAutoFixGroupIds, result.autoFixGroupIds);
      set(rawManualReviewGroupIds, result.manualReviewGroupIds);

      const [autoFixEventsMap, manualReviewEventsMap] = await Promise.all([
        fetchEventsForGroupIds(result.autoFixGroupIds),
        fetchEventsForGroupIds(result.manualReviewGroupIds),
      ]);

      set(autoFixEvents, autoFixEventsMap);
      set(manualReviewEvents, manualReviewEventsMap);
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
    autoFixDuplicates,
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    fixDuplicates,
    fixLoading,
    loading,
    manualReviewCount,
    manualReviewDuplicates,
    manualReviewGroupIds,
    totalCount,
  };
});
