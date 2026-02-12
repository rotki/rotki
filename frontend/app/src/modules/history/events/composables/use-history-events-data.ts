import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import type { Collection } from '@/types/collection';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { startPromise } from '@shared/utils';
import { flatten } from 'es-toolkit';
import { useHistoryEvents } from '@/composables/history/events';
import { useRefWithDebounce } from '@/composables/ref';
import { RequestCancelledError } from '@/modules/api/request-queue/errors';
import { api } from '@/modules/api/rotki-api';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';
import { logger } from '@/utils/logging';
import { useCompleteEvents } from './use-complete-events';

interface UseHistoryEventsDataOptions {
  groups: Ref<Collection<HistoryEventRow>>;
  pageParams: Ref<HistoryEventRequestPayload | undefined>;
  excludeIgnored: Ref<boolean>;
  groupLoading: Ref<boolean>;
  identifiers?: Ref<string[] | undefined>;
}

interface UseHistoryEventsDataReturn {
  // Loading states
  eventsLoading: Ref<boolean>;
  sectionLoading: ComputedRef<boolean>;
  loading: Readonly<Ref<boolean>>;

  // Collection data
  entriesFoundTotal: ComputedRef<number | undefined>;
  found: ComputedRef<number>;
  limit: ComputedRef<number>;
  total: ComputedRef<number>;
  showUpgradeRow: ComputedRef<boolean>;

  // Event data
  /**
   * All events grouped by groupIdentifier, including events with ignored assets.
   * Only hidden events are excluded. Used for operations like editing and redecoding
   * where the complete set of events is needed.
   */
  completeEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  /** Events grouped by groupIdentifier, with both hidden and ignored-asset events filtered out. */
  displayedEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  groupsWithHiddenIgnoredAssets: ComputedRef<Set<string>>;
  groupsShowingIgnoredAssets: Ref<Set<string>>;
  hasIgnoredEvent: ComputedRef<boolean>;
  groups: ComputedRef<HistoryEventEntry[]>;
  events: ComputedRef<HistoryEventEntry[]>;
  rawEvents: Ref<HistoryEventRow[]>;
  fetchEvents: () => Promise<void>;
  toggleShowIgnoredAssets: (groupId: string) => void;

  // Complete events helpers
  getGroupEvents: (groupId: string) => HistoryEventEntry[];
  getCompleteSubgroupEvents: (displayedEvents: HistoryEventEntry[]) => HistoryEventEntry[];
  getCompleteEventsForItem: (groupId: string, event: HistoryEventEntry) => HistoryEventEntry[];
}

export function useHistoryEventsData(
  options: UseHistoryEventsDataOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsDataReturn {
  const { excludeIgnored, groupLoading, groups, identifiers, pageParams } = options;

  const eventsLoading = ref<boolean>(false);
  const events = ref<HistoryEventRow[]>([]);
  let fetchVersion = 0;

  // Extract collection data
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
  const { data, entriesFoundTotal, found, limit, total } = getCollectionData(groups);
  const { showUpgradeRow } = setupEntryLimit(limit, found, total, entriesFoundTotal);
  const { fetchHistoryEvents } = useHistoryEvents();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { sectionLoading } = useHistoryEventsStatus();

  const groupIdentifiers = computed<string[]>(() =>
    get(data).flatMap(item => Array.isArray(item) ? item.map(i => i.groupIdentifier) : item.groupIdentifier),
  );

  const EVENTS_CANCEL_TAG = 'history-events-detail';

  // Fetches all events for the currently displayed groups.
  // limit: -1 fetches all matching events, but the scope is bounded by groupIdentifiers
  // which only includes groups visible on the current page.
  async function fetchEvents(): Promise<void> {
    const groupIds = get(groupIdentifiers);
    if (groupIds.length === 0) {
      set(events, []);
      return;
    }

    const currentVersion = ++fetchVersion;
    set(eventsLoading, true);
    api.cancelByTag(EVENTS_CANCEL_TAG);

    try {
      const response = await fetchHistoryEvents({
        ...get(pageParams),
        aggregateByGroupIds: false,
        excludeIgnoredAssets: false,
        groupIdentifiers: groupIds,
        identifiers: get(identifiers),
        limit: -1,
        offset: 0,
      }, { tags: [EVENTS_CANCEL_TAG] });

      if (currentVersion === fetchVersion)
        set(events, response.data);
    }
    catch (error: any) {
      if (!(error instanceof RequestCancelledError))
        logger.error(error);
    }
    finally {
      if (currentVersion === fetchVersion)
        set(eventsLoading, false);
    }
  }

  /**
   * All events grouped by groupIdentifier, including events with ignored assets.
   * Only hidden events are excluded. Used for operations like editing and redecoding
   * where the complete set of events is needed.
   */
  const completeEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => {
    const eventsList = get(events);
    if (eventsList.length === 0)
      return {};

    const mapping: Record<string, HistoryEventRow[]> = {};

    for (const event of eventsList) {
      if (Array.isArray(event)) {
        const visible = event.filter(({ hidden }) => !hidden);
        if (visible.length > 0) {
          const groupId = visible[0].groupIdentifier;
          (mapping[groupId] ??= []).push(visible);
        }
      }
      else if (!event.hidden) {
        (mapping[event.groupIdentifier] ??= []).push(event);
      }
    }

    return mapping;
  });

  // Track which groups have opted to show ignored assets (per-group toggle)
  const groupsShowingIgnoredAssets = shallowRef<Set<string>>(new Set());

  function toggleShowIgnoredAssets(groupId: string): void {
    const current = get(groupsShowingIgnoredAssets);
    const newSet = new Set(current);
    if (newSet.has(groupId))
      newSet.delete(groupId);
    else
      newSet.add(groupId);

    set(groupsShowingIgnoredAssets, newSet);
  }

  /** Events grouped by groupIdentifier, with both hidden and ignored-asset events filtered out. */
  const displayedEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => {
    const base = get(completeEventsMapped);
    if (!get(excludeIgnored))
      return base;

    const showingIgnored = get(groupsShowingIgnoredAssets);
    const mapping: Record<string, HistoryEventRow[]> = {};

    for (const [groupId, groupEvents] of Object.entries(base)) {
      // If this group is showing ignored assets, include all events
      if (showingIgnored.has(groupId)) {
        mapping[groupId] = groupEvents;
        continue;
      }

      const filtered: HistoryEventRow[] = [];
      for (const event of groupEvents) {
        if (Array.isArray(event)) {
          const visible = event.filter(item => !isAssetIgnored(item.asset));
          if (visible.length > 0)
            filtered.push(visible);
        }
        else if (!isAssetIgnored(event.asset)) {
          filtered.push(event);
        }
      }
      if (filtered.length > 0)
        mapping[groupId] = filtered;
    }

    return mapping;
  });

  const loading = useRefWithDebounce(logicOr(groupLoading, eventsLoading), 200);
  const hasIgnoredEvent = useArraySome(
    events,
    event => Array.isArray(event) ? event.some(item => item.ignoredInAccounting) : event.ignoredInAccounting,
  );

  function flattenedEventCount(rows: HistoryEventRow[]): number {
    let count = 0;
    for (const row of rows)
      count += Array.isArray(row) ? row.length : 1;

    return count;
  }

  // Track which groups have events hidden due to ignored assets filter
  const groupsWithHiddenIgnoredAssets = computed<Set<string>>(() => {
    if (!get(excludeIgnored))
      return new Set();

    const all = get(completeEventsMapped);
    const displayed = get(displayedEventsMapped);
    const result = new Set<string>();

    for (const groupId of Object.keys(all)) {
      const allCount = flattenedEventCount(all[groupId] ?? []);
      const displayedCount = flattenedEventCount(displayed[groupId] ?? []);
      if (allCount > displayedCount)
        result.add(groupId);
    }

    return result;
  });

  const flattenedGroups = computed<HistoryEventEntry[]>(() => flatten(get(data)));

  const flattenedEvents = computed<HistoryEventEntry[]>(() => flatten(get(events)));

  watch([data, found, itemsPerPage], ([dataValue, foundValue, itemsPerPageValue]) => {
    if (dataValue.length === 0 && foundValue > 0) {
      const lastPage = Math.ceil(foundValue / itemsPerPageValue);
      emit('set-page', lastPage);
    }
  });

  // Cancel stale events fetch as soon as new groups fetch starts
  watch(groupLoading, (loading) => {
    if (loading)
      api.cancelByTag(EVENTS_CANCEL_TAG);
  });

  // Trigger events fetch when groups change (tied to fetchData completion in pagination filter)
  watchImmediate(data, () => {
    startPromise(fetchEvents());
  });

  const { getCompleteEventsForItem, getCompleteSubgroupEvents, getGroupEvents } = useCompleteEvents(completeEventsMapped);

  return {
    completeEventsMapped,
    displayedEventsMapped,
    entriesFoundTotal,
    events: flattenedEvents,
    eventsLoading,
    fetchEvents,
    found,
    getCompleteEventsForItem,
    getCompleteSubgroupEvents,
    getGroupEvents,
    groups: flattenedGroups,
    groupsShowingIgnoredAssets,
    groupsWithHiddenIgnoredAssets,
    hasIgnoredEvent,
    limit,
    loading,
    rawEvents: events,
    sectionLoading,
    showUpgradeRow,
    toggleShowIgnoredAssets,
    total,
  };
}
