import type { ComputedRef, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventCollectionRow, HistoryEventEntry, HistoryEventEntryWithMeta } from '@/modules/history/events/schemas';
import { err, ok, type Result } from 'plainfp/result';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
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

interface UseCustomizedEventDuplicatesReturn {
  actionableCount: ComputedRef<number>;
  autoFixCount: ComputedRef<number>;
  autoFixGroupIds: ComputedRef<string[]>;
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
  /**
   * Fixes the groups (every auto-fixable one when none are given), then reads the group ids again.
   *
   * @remarks
   * Like the two below, it reports nothing itself: a success shows as the rows changing, and the
   * error it resolves to is for the surface that started it to name.
   */
  fixDuplicates: (groupIdentifiers?: string[]) => Promise<Result<void, unknown>>;
  fixLoading: Ref<boolean>;
  /** Marks the groups as not duplicates, then reads the group ids again. */
  ignoreDuplicates: (groupIdentifiers: string[]) => Promise<Result<void, unknown>>;
  ignoreLoading: Ref<boolean>;
  ignoredCount: ComputedRef<number>;
  ignoredGroupIds: ComputedRef<string[]>;
  loading: Ref<boolean>;
  manualReviewCount: ComputedRef<number>;
  manualReviewGroupIds: ComputedRef<string[]>;
  totalCount: ComputedRef<number>;
  /** Restores ignored groups, then reads the group ids again. */
  unignoreDuplicates: (groupIdentifiers: string[]) => Promise<Result<void, unknown>>;
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

  const fixDuplicates = async (groupIdentifiers?: string[]): Promise<Result<void, unknown>> => {
    set(fixLoading, true);
    try {
      await fixCustomizedEventDuplicates(groupIdentifiers);
      await fetchCustomizedEventDuplicates();
      return ok(undefined);
    }
    catch (error: unknown) {
      logger.error('Failed to fix customized event duplicates:', error);
      return err(error);
    }
    finally {
      set(fixLoading, false);
    }
  };

  const ignoreDuplicates = async (groupIdentifiers: string[]): Promise<Result<void, unknown>> => {
    set(ignoreLoading, true);
    try {
      await ignoreCustomizedEventDuplicates(groupIdentifiers);
      await fetchCustomizedEventDuplicates();
      return ok(undefined);
    }
    catch (error: unknown) {
      logger.error('Failed to ignore customized event duplicates:', error);
      return err(error);
    }
    finally {
      set(ignoreLoading, false);
    }
  };

  const unignoreDuplicates = async (groupIdentifiers: string[]): Promise<Result<void, unknown>> => {
    set(ignoreLoading, true);
    try {
      await unignoreCustomizedEventDuplicates(groupIdentifiers);
      await fetchCustomizedEventDuplicates();
      return ok(undefined);
    }
    catch (error: unknown) {
      logger.error('Failed to unignore customized event duplicates:', error);
      return err(error);
    }
    finally {
      set(ignoreLoading, false);
    }
  };

  return {
    actionableCount,
    autoFixCount,
    autoFixGroupIds,
    fetchCustomizedEventDuplicates,
    fetchDuplicateEvents,
    fetchError: shallowReadonly(fetchError),
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
