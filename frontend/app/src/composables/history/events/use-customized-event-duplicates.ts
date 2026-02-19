import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { Collection } from '@/types/collection';
import type { HistoryEventCollectionRow, HistoryEventEntry, HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { type CustomizedEventDuplicates, useCustomizedEventDuplicatesApi } from '@/composables/api/history/events/customized-event-duplicates';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { arrayify } from '@/utils/array';
import { logger } from '@/utils/logging';

export interface DuplicateRow {
  entry: HistoryEventEntry;
  groupIdentifier: string;
  location: string;
  locationLabel: string | null;
  timestamp: number;
  txHash: string;
}

export interface FetchDuplicateEventsPayload {
  groupIds: string[];
  limit: number;
  offset: number;
}

interface UseCustomizedEventDuplicatesReturn {
  actionableCount: ComputedRef<number>;
  autoFixCount: ComputedRef<number>;
  autoFixGroupIds: ComputedRef<string[]>;
  confirmAndFixDuplicate: (groupIdentifiers: string[], onSuccess?: () => void) => void;
  confirmAndMarkNonDuplicated: (groupIdentifiers: string[], onSuccess?: () => void) => void;
  confirmAndRestore: (groupIdentifiers: string[], onSuccess?: () => void) => void;
  fetchCustomizedEventDuplicates: () => Promise<void>;
  fetchDuplicateEvents: (payload: FetchDuplicateEventsPayload) => Promise<Collection<DuplicateRow>>;
  fixDuplicates: (groupIdentifiers?: string[]) => Promise<ActionStatus>;
  fixLoading: Ref<boolean>;
  ignoreDuplicates: (groupIdentifiers: string[]) => Promise<ActionStatus>;
  ignoreLoading: Ref<boolean>;
  ignoredCount: ComputedRef<number>;
  ignoredGroupIds: ComputedRef<string[]>;
  loading: Ref<boolean>;
  manualReviewCount: ComputedRef<number>;
  manualReviewGroupIds: ComputedRef<string[]>;
  totalCount: ComputedRef<number>;
  unignoreDuplicates: (groupIdentifiers: string[]) => Promise<ActionStatus>;
}

function getEventEntry(row: HistoryEventCollectionRow): HistoryEventEntryWithMeta {
  return Array.isArray(row) ? row[0] : row;
}

function mapToDuplicateRow(groupId: string, events: HistoryEventCollectionRow): DuplicateRow {
  const { entry, ...meta } = getEventEntry(events);
  const eventEntry: HistoryEventEntry = { ...entry, ...meta };
  return {
    entry: eventEntry,
    groupIdentifier: groupId,
    location: entry.location,
    locationLabel: entry.locationLabel ?? null,
    timestamp: entry.timestamp,
    txHash: 'txRef' in entry ? (entry.txRef ?? '') : '',
  };
}

export const useCustomizedEventDuplicates = createSharedComposable((): UseCustomizedEventDuplicatesReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { show: showConfirm } = useConfirmStore();
  const { setMessage } = useMessageStore();

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const { fixCustomizedEventDuplicates, getCustomizedEventDuplicates, ignoreCustomizedEventDuplicates, unignoreCustomizedEventDuplicates } = useCustomizedEventDuplicatesApi();

  const rawAutoFixGroupIds = ref<string[]>([]);
  const rawManualReviewGroupIds = ref<string[]>([]);
  const rawIgnoredGroupIds = ref<string[]>([]);
  const loading = ref<boolean>(false);
  const fixLoading = ref<boolean>(false);
  const ignoreLoading = ref<boolean>(false);

  const autoFixGroupIds = computed<string[]>(() => get(rawAutoFixGroupIds));
  const manualReviewGroupIds = computed<string[]>(() => get(rawManualReviewGroupIds));
  const ignoredGroupIds = computed<string[]>(() => get(rawIgnoredGroupIds));

  const autoFixCount = computed<number>(() => get(rawAutoFixGroupIds).length);
  const manualReviewCount = computed<number>(() => get(rawManualReviewGroupIds).length);
  const ignoredCount = computed<number>(() => get(rawIgnoredGroupIds).length);
  const actionableCount = computed<number>(() => get(autoFixCount) + get(manualReviewCount));
  const totalCount = computed<number>(() => get(actionableCount) + get(ignoredCount));

  const fetchCustomizedEventDuplicates = async (): Promise<void> => {
    set(loading, true);
    try {
      const result: CustomizedEventDuplicates = await getCustomizedEventDuplicates();
      set(rawAutoFixGroupIds, result.autoFixGroupIds);
      set(rawManualReviewGroupIds, result.manualReviewGroupIds);
      set(rawIgnoredGroupIds, result.ignoredGroupIds);
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

  const ignoreDuplicates = async (groupIdentifiers: string[]): Promise<ActionStatus> => {
    set(ignoreLoading, true);
    try {
      await ignoreCustomizedEventDuplicates(groupIdentifiers);
      await fetchCustomizedEventDuplicates();
      return { success: true };
    }
    catch (error: any) {
      logger.error('Failed to ignore customized event duplicates:', error);
      setMessage({
        description: t('actions.customized_event_duplicates.mark_non_duplicated_error.description', { error: error.message }),
        title: t('actions.customized_event_duplicates.mark_non_duplicated_error.title'),
      });
      return { message: error.message, success: false };
    }
    finally {
      set(ignoreLoading, false);
    }
  };

  const unignoreDuplicates = async (groupIdentifiers: string[]): Promise<ActionStatus> => {
    set(ignoreLoading, true);
    try {
      await unignoreCustomizedEventDuplicates(groupIdentifiers);
      await fetchCustomizedEventDuplicates();
      return { success: true };
    }
    catch (error: any) {
      logger.error('Failed to unignore customized event duplicates:', error);
      setMessage({
        description: t('actions.customized_event_duplicates.unignore_error.description', { error: error.message }),
        title: t('actions.customized_event_duplicates.unignore_error.title'),
      });
      return { message: error.message, success: false };
    }
    finally {
      set(ignoreLoading, false);
    }
  };

  const confirmAndFixDuplicate = (groupIdentifiers: string[], onSuccess?: () => void): void => {
    showConfirm({
      message: groupIdentifiers.length === 1
        ? t('customized_event_duplicates.actions.fix_single_confirm')
        : t('customized_event_duplicates.actions.fix_selected_confirm', { count: groupIdentifiers.length }),
      primaryAction: t('common.actions.confirm'),
      title: groupIdentifiers.length === 1
        ? t('customized_event_duplicates.actions.fix_single')
        : t('customized_event_duplicates.actions.fix_selected'),
    }, async () => {
      const result = await fixDuplicates(groupIdentifiers);
      if (result.success)
        onSuccess?.();
    });
  };

  const confirmAndMarkNonDuplicated = (groupIdentifiers: string[], onSuccess?: () => void): void => {
    showConfirm({
      message: groupIdentifiers.length === 1
        ? t('customized_event_duplicates.actions.mark_non_duplicated_confirm')
        : t('customized_event_duplicates.actions.mark_non_duplicated_selected_confirm', { count: groupIdentifiers.length }),
      primaryAction: t('common.actions.confirm'),
      title: groupIdentifiers.length === 1
        ? t('customized_event_duplicates.actions.mark_non_duplicated')
        : t('customized_event_duplicates.actions.mark_non_duplicated_selected'),
    }, async () => {
      const result = await ignoreDuplicates(groupIdentifiers);
      if (result.success)
        onSuccess?.();
    });
  };

  const confirmAndRestore = (groupIdentifiers: string[], onSuccess?: () => void): void => {
    showConfirm({
      message: groupIdentifiers.length === 1
        ? t('customized_event_duplicates.actions.restore_confirm')
        : t('customized_event_duplicates.actions.restore_selected_confirm', { count: groupIdentifiers.length }),
      primaryAction: t('common.actions.confirm'),
      title: groupIdentifiers.length === 1
        ? t('customized_event_duplicates.actions.restore')
        : t('customized_event_duplicates.actions.restore_selected'),
    }, async () => {
      const result = await unignoreDuplicates(groupIdentifiers);
      if (result.success)
        onSuccess?.();
    });
  };

  return {
    actionableCount,
    autoFixCount,
    autoFixGroupIds,
    confirmAndFixDuplicate,
    confirmAndMarkNonDuplicated,
    confirmAndRestore,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    fixDuplicates,
    fixLoading,
    ignoreDuplicates,
    ignoreLoading,
    ignoredCount,
    ignoredGroupIds,
    loading,
    manualReviewCount,
    manualReviewGroupIds,
    totalCount,
    unignoreDuplicates,
  };
});
