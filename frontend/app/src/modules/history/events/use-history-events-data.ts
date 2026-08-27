import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import { HistoryEventEntryType } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { flatten } from 'es-toolkit';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { api } from '@/modules/core/api/rotki-api';
import { getCollectionData, setupEntryLimit } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useSetting } from '@/modules/settings/use-setting';
import { useCompleteEvents } from './use-complete-events';

interface UseHistoryEventsDataOptions {
  /** Paginated group collection owned by the caller's pagination filter; its group identifiers scope the per-group event fetch and any change retriggers it. */
  groups: MaybeRefOrGetter<Collection<HistoryEventRow>>;
  /** Current filter payload, reused as the base of the event fetch so the detail query matches the group query. */
  requestPayload: MaybeRefOrGetter<HistoryEventRequestPayload | undefined>;
  /** When true, events whose asset is ignored are filtered out of the displayed mapping unless the user reveals them per group. */
  excludeIgnored: MaybeRefOrGetter<boolean>;
  /** Whether the caller is fetching groups; turning true cancels the in-flight event fetch and it feeds the debounced combined `loading`. */
  groupLoading: MaybeRefOrGetter<boolean>;
  /** Restricts the event fetch to these identifiers; undefined loads every event belonging to the groups on the current page. */
  identifiers?: MaybeRefOrGetter<string[] | undefined>;
}

interface UseHistoryEventsDataReturn {
  eventsLoading: Readonly<Ref<boolean>>;
  sectionLoading: ComputedRef<boolean>;
  loading: Readonly<Ref<boolean>>;

  entriesFoundTotal: ComputedRef<number | undefined>;
  found: ComputedRef<number>;
  limit: ComputedRef<number>;
  total: ComputedRef<number>;
  showUpgradeRow: ComputedRef<boolean>;

  /**
   * All events grouped by groupIdentifier, including events with ignored assets.
   * Only hidden events are excluded. Used for operations like editing and redecoding
   * where the complete set of events is needed.
   */
  completeEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  /** Events grouped by groupIdentifier, with both hidden and ignored-asset events filtered out. */
  displayedEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  groupsWithHiddenIgnoredAssets: ComputedRef<Set<string>>;
  groupsShowingIgnoredAssets: ComputedRef<Set<string>>;
  hasIgnoredEvent: ComputedRef<boolean>;
  groups: ComputedRef<HistoryEventEntry[]>;
  events: ComputedRef<HistoryEventEntry[]>;
  rawEvents: Readonly<Ref<HistoryEventRow[]>>;
  fetchEvents: () => Promise<void>;
  toggleShowIgnoredAssets: (groupId: string) => void;

  getGroupEvents: (groupId: string) => HistoryEventEntry[];
  getCompleteSubgroupEvents: (displayedEvents: HistoryEventEntry[]) => HistoryEventEntry[];
  getCompleteEventsForItem: (groupId: string, event: HistoryEventEntry) => HistoryEventEntry[];
  isSubgroupIncomplete: (displayedEvents: HistoryEventEntry[]) => boolean;
}

function isSwapOnlyGroup(events: HistoryEventRow[]): events is HistoryEventEntry[] {
  return events.length > 1 && events.every(e => !Array.isArray(e) && e.entryType === HistoryEventEntryType.SWAP_EVENT);
}

export function useHistoryEventsData(
  options: UseHistoryEventsDataOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsDataReturn {
  const { excludeIgnored, groupLoading, groups, identifiers, requestPayload } = options;

  const eventsLoading = shallowRef<boolean>(false);
  const events = ref<HistoryEventRow[]>([]);
  let fetchVersion = 0;

  const itemsPerPage = useSetting('itemsPerPage');
  const { data, entriesFoundTotal, found, limit, total } = getCollectionData(groups);
  const { showUpgradeRow } = setupEntryLimit(limit, found, total, entriesFoundTotal);
  const { fetchHistoryEvents } = useHistoryEvents();
  const ignoredAssetsStore = useAssetsStore();
  const { isAssetIgnored } = ignoredAssetsStore;
  const { ignoredAssets } = storeToRefs(ignoredAssetsStore);
  const { sectionLoading } = useHistoryEventsStatus();

  const groupIdentifiers = computed<string[]>(() =>
    get(data).flatMap(item => Array.isArray(item) ? item.map(i => i.groupIdentifier) : item.groupIdentifier),
  );

  const EVENTS_CANCEL_TAG = 'history-events-detail';

  /**
   * Fetches every event belonging to the groups currently on screen.
   *
   * @remarks
   * `limit: -1` lifts the page bound, which stays safe because `groupIdentifiers` already narrows
   * the request to the groups the visible page holds. A later call supersedes an in-flight one:
   * the response is discarded unless its version is still the current one.
   */
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
        ...toValue(requestPayload),
        aggregateByGroupIds: false,
        excludeIgnoredAssets: false,
        groupIdentifiers: groupIds,
        identifiers: toValue(identifiers),
        limit: -1,
        offset: 0,
      }, { tags: [EVENTS_CANCEL_TAG] });

      if (currentVersion === fetchVersion)
        set(events, response.data);
    }
    catch (error: unknown) {
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
   *
   * @remarks
   * A swap group is wrapped as a single subgroup here: the backend does not subgroup one, every
   * event in it already belonging to the same subgroup, and `HistoryEventsSwapItem` renders it
   * that way.
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

    for (const [groupId, groupEvents] of Object.entries(mapping)) {
      if (isSwapOnlyGroup(groupEvents))
        mapping[groupId] = [groupEvents];
    }

    return mapping;
  });

  // The only mutable state here: which groups the user toggled open. The rest is derived.
  const showIgnoredAssetsIntent = shallowRef<Set<string>>(new Set());

  // Groups that currently contain at least one event with an ignored asset.
  const groupsWithIgnoredAssets = computed<Set<string>>(() => {
    const result = new Set<string>();
    for (const [groupId, rows] of Object.entries(get(completeEventsMapped))) {
      const hasIgnored = rows.some(row => Array.isArray(row)
        ? row.some(item => isAssetIgnored(item.asset))
        : isAssetIgnored(row.asset));
      if (hasIgnored)
        result.add(groupId);
    }
    return result;
  });

  // Intent intersected with reality, so unignoring an asset drops the group with no cleanup.
  const groupsShowingIgnoredAssets = computed<Set<string>>(() => {
    const valid = get(groupsWithIgnoredAssets);
    return new Set([...get(showIgnoredAssetsIntent)].filter(groupId => valid.has(groupId)));
  });

  // Groups holding an ignored asset the per-group toggle has not revealed.
  const groupsWithHiddenIgnoredAssets = computed<Set<string>>(() => {
    if (!toValue(excludeIgnored))
      return new Set();

    const showing = get(groupsShowingIgnoredAssets);
    return new Set([...get(groupsWithIgnoredAssets)].filter(groupId => !showing.has(groupId)));
  });

  function toggleShowIgnoredAssets(groupId: string): void {
    const next = new Set(get(showIgnoredAssetsIntent));
    if (next.has(groupId))
      next.delete(groupId);
    else
      next.add(groupId);

    set(showIgnoredAssetsIntent, next);
  }

  /** Events grouped by groupIdentifier, with both hidden and ignored-asset events filtered out. */
  const displayedEventsMapped = computed<Record<string, HistoryEventRow[]>>(() => {
    const base = get(completeEventsMapped);
    if (!toValue(excludeIgnored))
      return base;

    const showingIgnored = get(groupsShowingIgnoredAssets);
    const mapping: Record<string, HistoryEventRow[]> = {};

    for (const [groupId, groupEvents] of Object.entries(base)) {
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

  // Map each event identifier to its complete subgroup size for detecting incomplete subgroups
  const completeSubgroupSizes = computed<Map<number, number>>(() => {
    const map = new Map<number, number>();
    for (const groupEvents of Object.values(get(completeEventsMapped))) {
      for (const event of groupEvents) {
        if (!Array.isArray(event))
          continue;

        for (const subEvent of event)
          map.set(subEvent.identifier, event.length);
      }
    }
    return map;
  });

  /**
   * Checks if a displayed subgroup has fewer events than the complete subgroup
   * (i.e., some events are hidden due to ignored asset filtering).
   * When true, the subgroup should always be shown expanded without a collapse toggle.
   */
  function isSubgroupIncomplete(displayedEvents: HistoryEventEntry[]): boolean {
    if (displayedEvents.length === 0)
      return false;
    const sizes = get(completeSubgroupSizes);
    const completeSize = sizes.get(displayedEvents[0].identifier);
    return completeSize !== undefined && completeSize > displayedEvents.length;
  }

  const flattenedGroups = computed<HistoryEventEntry[]>(() => flatten(get(data)));

  const flattenedEvents = computed<HistoryEventEntry[]>(() => flatten(get(events)));

  watch([data, found, itemsPerPage], ([dataValue, foundValue, itemsPerPageValue]) => {
    if (dataValue.length === 0 && foundValue > 0) {
      const lastPage = Math.ceil(foundValue / itemsPerPageValue);
      emit('set-page', lastPage);
    }
  });

  // Cancel stale events fetch as soon as new groups fetch starts
  watch(() => toValue(groupLoading), (loading) => {
    if (loading)
      api.cancelByTag(EVENTS_CANCEL_TAG);
  });

  // Trigger events fetch when groups change (tied to fetchData completion in pagination filter)
  watchImmediate(data, () => {
    startPromise(fetchEvents());
  });

  // Watched on the store, not the child's emit: marking spam destroys the row before it propagates.
  watch(ignoredAssets, () => {
    emit('refresh');
  });

  const { getCompleteEventsForItem, getCompleteSubgroupEvents, getGroupEvents } = useCompleteEvents(completeEventsMapped);

  return {
    completeEventsMapped,
    displayedEventsMapped,
    entriesFoundTotal,
    events: flattenedEvents,
    eventsLoading: readonly(eventsLoading),
    fetchEvents,
    found,
    getCompleteEventsForItem,
    getCompleteSubgroupEvents,
    getGroupEvents,
    groups: flattenedGroups,
    groupsShowingIgnoredAssets,
    groupsWithHiddenIgnoredAssets,
    hasIgnoredEvent,
    isSubgroupIncomplete,
    limit,
    loading,
    rawEvents: shallowReadonly(events),
    sectionLoading,
    showUpgradeRow,
    toggleShowIgnoredAssets,
    total,
  };
}
