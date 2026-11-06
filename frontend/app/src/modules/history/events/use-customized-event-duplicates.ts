import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventCollectionRow, HistoryEventEntry, HistoryEventEntryWithMeta } from '@/modules/history/events/schemas';
import type { HistoryEventsActionFailure } from '@/modules/history/events/use-history-events-action-failure';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { type CustomizedEventDuplicates, useCustomizedEventDuplicatesApi } from '@/modules/history/api/events/use-customized-event-duplicates-api';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';

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

/**
 * What runs once a duplicates action settles.
 *
 * @remarks
 * The action reports nothing itself: a success shows as the rows changing, and a failure goes to
 * `onFailure`, for the surface that asked to name it.
 */
export interface DuplicatesActionHandlers {
  onSuccess?: () => void;
  onFailure?: (failure: HistoryEventsActionFailure) => void;
}

interface UseCustomizedEventDuplicatesReturn {
  actionableCount: ComputedRef<number>;
  autoFixCount: ComputedRef<number>;
  autoFixGroupIds: ComputedRef<string[]>;
  /** Fixes the groups, once the button that started it asked (see `useDuplicatesQuestion`). */
  fixAndSettle: (groupIdentifiers: string[], handlers?: DuplicatesActionHandlers) => Promise<void>;
  /** Marks the groups as not duplicates, once the button that started it asked. */
  markNonDuplicatedAndSettle: (groupIdentifiers: string[], handlers?: DuplicatesActionHandlers) => Promise<void>;
  /** Restores ignored groups, once the button that started it asked. */
  restoreAndSettle: (groupIdentifiers: string[], handlers?: DuplicatesActionHandlers) => Promise<void>;
  fetchCustomizedEventDuplicates: () => Promise<void>;
  /**
   * Why the last read of the duplicate group ids failed, kept until a read succeeds.
   *
   * @remarks
   * The action center refreshes these ids in the background, so a failure is kept for the dialog to
   * show rather than interrupting the user.
   */
  fetchError: Readonly<Ref<unknown>>;
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

  const { fetchHistoryEvents } = useHistoryEventsApi();
  const { fixCustomizedEventDuplicates, getCustomizedEventDuplicates, ignoreCustomizedEventDuplicates, unignoreCustomizedEventDuplicates } = useCustomizedEventDuplicatesApi();

  const rawAutoFixGroupIds = ref<string[]>([]);
  const rawManualReviewGroupIds = ref<string[]>([]);
  const rawIgnoredGroupIds = ref<string[]>([]);
  const loading = ref<boolean>(false);
  const fetchError = shallowRef<unknown>();
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
      set(fetchError, undefined);
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return;
      logger.error('Failed to fetch customized event duplicates:', error);
      set(fetchError, error);
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
      await fixCustomizedEventDuplicates(groupIdentifiers);
      await fetchCustomizedEventDuplicates();

      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to fix customized event duplicates:', error);
      return { message, success: false };
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
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to ignore customized event duplicates:', error);
      return { message, success: false };
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
    catch (error: unknown) {
      const message = getErrorMessage(error);
      logger.error('Failed to unignore customized event duplicates:', error);
      return { message, success: false };
    }
    finally {
      set(ignoreLoading, false);
    }
  };

  /** Hands a settled action to the handlers, a failure under `title`. */
  function settle(result: ActionStatus, title: string, handlers: DuplicatesActionHandlers): void {
    if (result.success)
      handlers.onSuccess?.();
    else
      handlers.onFailure?.({ failure: result.message, title });
  }

  const fixAndSettle = async (groupIdentifiers: string[], handlers: DuplicatesActionHandlers = {}): Promise<void> => {
    settle(await fixDuplicates(groupIdentifiers), t('actions.customized_event_duplicates.fix_error.title'), handlers);
  };

  const markNonDuplicatedAndSettle = async (groupIdentifiers: string[], handlers: DuplicatesActionHandlers = {}): Promise<void> => {
    settle(await ignoreDuplicates(groupIdentifiers), t('actions.customized_event_duplicates.mark_non_duplicated_error.title'), handlers);
  };

  const restoreAndSettle = async (groupIdentifiers: string[], handlers: DuplicatesActionHandlers = {}): Promise<void> => {
    settle(await unignoreDuplicates(groupIdentifiers), t('actions.customized_event_duplicates.unignore_error.title'), handlers);
  };

  return {
    actionableCount,
    autoFixCount,
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    fetchError: shallowReadonly(fetchError),
    fixAndSettle,
    fixDuplicates,
    fixLoading,
    ignoreDuplicates,
    ignoreLoading,
    ignoredCount,
    ignoredGroupIds,
    loading,
    manualReviewCount,
    manualReviewGroupIds,
    markNonDuplicatedAndSettle,
    restoreAndSettle,
    totalCount,
    unignoreDuplicates,
  };
});
