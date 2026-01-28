import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import type { Collection } from '@/types/collection';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { flatten } from 'es-toolkit';
import { useHistoryEvents } from '@/composables/history/events';
import { useRefWithDebounce } from '@/composables/ref';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

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
  allEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  displayedEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  hasIgnoredEvent: ComputedRef<boolean>;
  groups: ComputedRef<HistoryEventEntry[]>;
  events: ComputedRef<HistoryEventEntry[]>;
  rawEvents: Ref<HistoryEventRow[]>;
}

export function useHistoryEventsData(
  options: UseHistoryEventsDataOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsDataReturn {
  const { excludeIgnored, groupLoading, groups, identifiers, pageParams } = options;

  const eventsLoading = ref<boolean>(false);

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

  // Fetches all events for the currently displayed groups.
  // limit: -1 fetches all matching events, but the scope is bounded by groupIdentifiers
  // which only includes groups visible on the current page.
  const events: Ref<HistoryEventRow[]> = asyncComputed(async () => {
    const groupIds = get(groupIdentifiers);

    if (groupIds.length === 0)
      return [];

    const response = await fetchHistoryEvents({
      ...get(pageParams),
      aggregateByGroupIds: false,
      excludeIgnoredAssets: false,
      groupIdentifiers: groupIds,
      identifiers: get(identifiers),
      limit: -1,
      offset: 0,
    });

    return response.data;
  }, [], {
    evaluating: eventsLoading,
    lazy: true,
  });

  // Groups events by their groupIdentifier, filtering out hidden events
  const allEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => {
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

  // Derives from allEventsMapped, filtering out ignored assets when excludeIgnored is true
  const displayedEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => {
    const base = get(allEventsMapped);
    if (!get(excludeIgnored))
      return base;

    const mapping: Record<string, HistoryEventRow[]> = {};

    for (const [groupId, groupEvents] of Object.entries(base)) {
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

  const loading = useRefWithDebounce(logicOr(groupLoading, eventsLoading), 100);
  const hasIgnoredEvent = useArraySome(events, event => Array.isArray(event) && event.some(item => item.ignoredInAccounting));

  const flattenedGroups = computed<HistoryEventEntry[]>(() => flatten(get(data)));

  const flattenedEvents = computed<HistoryEventEntry[]>(() => flatten(get(events)));

  watch([data, found, itemsPerPage], ([dataValue, foundValue, itemsPerPageValue]) => {
    if (dataValue.length === 0 && foundValue > 0) {
      const lastPage = Math.ceil(foundValue / itemsPerPageValue);
      emit('set-page', lastPage);
    }
  });

  return {
    allEventsMapped,
    displayedEventsMapped,
    entriesFoundTotal,
    events: flattenedEvents,
    eventsLoading,
    found,
    groups: flattenedGroups,
    hasIgnoredEvent,
    limit,
    loading,
    rawEvents: events,
    sectionLoading,
    showUpgradeRow,
    total,
  };
}
