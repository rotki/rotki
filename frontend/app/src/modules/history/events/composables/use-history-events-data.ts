import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { Collection } from '@/types/collection';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventsTableEmitFn } from './types';
import { useHistoryEvents } from '@/composables/history/events';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';
import { flatten } from 'es-toolkit';

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
  eventsGroupedByEventIdentifier: ComputedRef<Record<string, HistoryEventRow[]>>;
  hasIgnoredEvent: ComputedRef<boolean>;
  groups: ComputedRef<HistoryEventEntry[]>;
  events: ComputedRef<HistoryEventEntry[]>;
}

export function useHistoryEventsData(
  options: UseHistoryEventsDataOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsDataReturn {
  const { excludeIgnored, groupLoading, groups, identifiers, pageParams } = options;

  const eventsLoading = ref<boolean>(false);

  // Extract collection data
  const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
  const { isLoading } = useStatusStore();
  const { data, entriesFoundTotal, found, limit, total } = getCollectionData(groups);
  const { showUpgradeRow } = setupEntryLimit(limit, found, total, entriesFoundTotal);
  const { fetchHistoryEvents } = useHistoryEvents();

  const sectionLoading = computed(() => get(isLoading(Section.HISTORY)));

  const events: Ref<HistoryEventRow[]> = asyncComputed(async () => {
    const dataValue = get(data);

    if (dataValue.length === 0)
      return [];

    const response = await fetchHistoryEvents({
      ...get(pageParams),
      eventIdentifiers: dataValue.flatMap(item => Array.isArray(item) ? item.map(i => i.eventIdentifier) : item.eventIdentifier),
      excludeIgnoredAssets: get(excludeIgnored),
      groupByEventIds: false,
      identifiers: get(identifiers),
      limit: -1,
      offset: 0,
    });

    return response.data;
  }, [], {
    evaluating: eventsLoading,
    lazy: true,
  });

  function addEventToMapping(mapping: Record<string, HistoryEventRow[]>, eventId: string, event: HistoryEventRow): void {
    const existing = mapping[eventId];
    if (existing)
      existing.push(event);
    else
      mapping[eventId] = [event];
  }

  function processArrayEvent(event: HistoryEventEntry[], mapping: Record<string, HistoryEventRow[]>): void {
    const filtered = event.filter(({ hidden }) => !hidden);
    if (filtered.length > 0) {
      const eventId = filtered[0].eventIdentifier;
      addEventToMapping(mapping, eventId, filtered);
    }
  }

  function processSingleEvent(event: HistoryEventEntry, mapping: Record<string, HistoryEventRow[]>): void {
    if (!event.hidden) {
      const eventId = event.eventIdentifier;
      addEventToMapping(mapping, eventId, event);
    }
  }

  const eventsGroupedByEventIdentifier = computed<Record<string, HistoryEventRow[]>>(() => {
    const eventsList = get(events);

    if (eventsList.length === 0)
      return {};

    const mapping: Record<string, HistoryEventRow[]> = {};

    for (const event of eventsList) {
      if (Array.isArray(event)) {
        processArrayEvent(event, mapping);
      }
      else {
        processSingleEvent(event, mapping);
      }
    }

    return mapping;
  });

  const loading = refDebounced(logicOr(groupLoading, eventsLoading), 100);
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
    entriesFoundTotal,
    events: flattenedEvents,
    eventsGroupedByEventIdentifier,
    eventsLoading,
    found,
    groups: flattenedGroups,
    hasIgnoredEvent,
    limit,
    loading,
    sectionLoading,
    showUpgradeRow,
    total,
  };
}
