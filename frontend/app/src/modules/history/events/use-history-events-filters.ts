import type { Account, HistoryEventEntryType } from '@rotki/common';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { objectOmit } from '@vueuse/shared';
import { isEqual } from 'es-toolkit';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { type Filters, type Matcher, useHistoryEventFilter } from '@/modules/core/table/filters/use-events-filter';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';
import { type ChangeSource, routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';
import {
  isEvmEventType,
  isOnlineHistoryEventType,
} from '@/modules/history/event-utils';
import { DuplicateHandlingStatus, type HighlightType } from '@/modules/history/events/action-types';
import { buildHistoryEventSources } from '@/modules/history/events/history-event-query';
import { useHistoryEventHighlights, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

export { useHistoryEventNavigationConsumer } from '@/modules/history/events/use-history-event-navigation-consumer';

type Period = { fromTimestamp?: string; toTimestamp?: string } | { fromTimestamp?: number; toTimestamp?: number };

interface HistoryEventsFiltersOptions {
  entryTypes: MaybeRefOrGetter<HistoryEventEntryType[] | undefined>;
  eventSubTypes: MaybeRefOrGetter<string[]>;
  eventTypes: MaybeRefOrGetter<string[]>;
  externalAccountFilter: MaybeRefOrGetter<Account[]>;
  location: MaybeRefOrGetter<string | undefined>;
  mainPage: MaybeRefOrGetter<boolean>;
  period: MaybeRefOrGetter<Period | undefined>;
  protocols: MaybeRefOrGetter<string[]>;
  useExternalAccountFilter: MaybeRefOrGetter<boolean | undefined>;
  validators: MaybeRefOrGetter<number[] | undefined>;
}

export function getDefaultToggles(): HistoryEventsToggles {
  return {
    matchExactEvents: false,
    showIgnoredAssets: false,
    stateMarkers: [],
  };
}

interface UseHistoryEventsFiltersReturn {
  clearFilters: () => void;
  duplicateHandlingStatus: ComputedRef<DuplicateHandlingStatus | undefined>;
  locationLabels: Readonly<Ref<string[]>>;
  groupIdentifiers: ComputedRef<string[] | undefined>;
  refetch: () => Promise<void>;
  filters: ComputedRef<Filters>;
  groupLoading: Ref<boolean>;
  groups: Ref<Collection<HistoryEventRow>>;
  hasActiveFilters: ComputedRef<boolean>;
  highlightedGroupIdentifier: ComputedRef<string | undefined>;
  highlightedIdentifiers: ComputedRef<string[] | undefined>;
  highlightTypes: ComputedRef<Record<string, HighlightType>>;
  identifiers: ComputedRef<string[] | undefined>;
  includes: ComputedRef<{ evmEvents: boolean; onlineEvents: boolean }>;
  locations: ComputedRef<string[]>;
  matchers: ComputedRef<Matcher[]>;
  onLocationLabelsChanged: (locationLabels: string[]) => void;
  requestPayload: ComputedRef<HistoryEventRequestPayload>;
  pagination: ComputedRef<TablePaginationData>;
  setPage: (page: number, source?: ChangeSource) => void;
  sort: ComputedRef<DataTableSortData<HistoryEventRow>>;
  setFilter: (newFilter: Filters) => void;
  usedLocationLabels: ComputedRef<string[]>;
}

export function useHistoryEventsFilters(
  options: HistoryEventsFiltersOptions,
  toggles: Ref<HistoryEventsToggles>,
  overlayMode: Ref<OverlayMode> = ref<OverlayMode>(OverlayMode.NONE),
): UseHistoryEventsFiltersReturn {
  const {
    entryTypes,
    eventSubTypes,
    eventTypes,
    externalAccountFilter,
    location,
    mainPage,
    period,
    protocols,
    useExternalAccountFilter,
    validators,
  } = options;

  const locationLabels = ref<string[]>([]);

  const GROUPS_CANCEL_TAG = 'history-events-groups';

  const route = useRoute();
  const { fetchHistoryEvents } = useHistoryEvents();
  const { clearAllHighlightTargets, isNavigating } = useHistoryEventNavigation();

  const highlightKeys = ['highlightedAccountingEvent', 'highlightedAssetMovement', 'highlightedInternalTxConflict', 'highlightedPotentialMatch', 'highlightedNegativeBalanceEvent'] as const;
  const shouldPreserveHighlights = ref<boolean>(highlightKeys.some(key => !!get(route).query[key]));

  const fetchHistoryEventsTagged = async (
    payload: MaybeRef<HistoryEventRequestPayload>,
  ): Promise<Collection<HistoryEventRow>> =>
    fetchHistoryEvents(payload, { tags: [GROUPS_CANCEL_TAG] });

  // Define these early since they're used in extraParams / requestParams
  const missingAcquisitionFromQuery = computed<string[] | undefined>(() => {
    const { missingAcquisitionIdentifier } = get(route).query;
    return missingAcquisitionIdentifier ? [missingAcquisitionIdentifier as string] : undefined;
  });

  const groupIdentifiersRaw = computed<string | undefined>(() => {
    const { groupIdentifiers } = get(route).query;
    return groupIdentifiers ? (groupIdentifiers as string) : undefined;
  });

  const groupIdentifiersFromQuery = computed<string[] | undefined>(() => {
    const raw = get(groupIdentifiersRaw);
    if (!raw)
      return undefined;

    return raw.includes(',') ? raw.split(',') : [raw];
  });

  const duplicateHandlingStatusFromQuery = computed<DuplicateHandlingStatus | undefined>(() => {
    const { duplicateHandlingStatus } = get(route).query;
    if (duplicateHandlingStatus === DuplicateHandlingStatus.AUTO_FIX)
      return DuplicateHandlingStatus.AUTO_FIX;
    if (duplicateHandlingStatus === DuplicateHandlingStatus.MANUAL_REVIEW)
      return DuplicateHandlingStatus.MANUAL_REVIEW;
    return undefined;
  });

  const usedLocationLabels = computed<string[]>(() => {
    if (toValue(useExternalAccountFilter))
      return toValue(externalAccountFilter).map(account => account.address);

    return get(locationLabels);
  });

  const sources = buildHistoryEventSources({
    duplicateHandlingStatusFromQuery,
    entryTypes,
    eventSubTypes,
    eventTypes,
    groupIdentifiersFromQuery,
    location,
    locationLabels,
    missingAcquisitionFromQuery,
    overlayMode,
    period,
    protocols,
    route,
    shouldPreserveHighlights,
    toggles,
    usedLocationLabels,
    validators,
  });

  const filterSchema = useHistoryEventFilter({
    eventSubtypes: (toValue(eventSubTypes) || []).length > 0,
    eventTypes: (toValue(eventTypes) || []).length > 0,
    locations: !!toValue(location),
    period: !!toValue(period),
    protocols: (toValue(protocols) || []).length > 0,
    validators: !!toValue(validators),
  }, computed<HistoryEventEntryType[] | undefined>(() => toValue(entryTypes)));

  const { matchers } = filterSchema;

  const {
    collection: groups,
    filter: filters,
    isLoading: groupLoading,
    markUserIntent,
    pagination,
    refetch,
    requestPayload,
    setFilter,
    setPage,
    sort,
  } = useServerTable<
    HistoryEventRow,
    HistoryEventRequestPayload,
    Filters,
    Matcher
  >({
    fetch: fetchHistoryEventsTagged,
    filterSchema,
    params: sources,
    persist: {
      keys: {
        duplicateHandlingStatus: 'never',
        groupIdentifiers: 'never',
        highlightedAccountingEvent: 'never',
        highlightedAssetMovement: 'never',
        highlightedInternalTxConflict: 'never',
        highlightedNegativeBalanceEvent: 'never',
        highlightedPotentialMatch: 'never',
        missingAcquisitionIdentifier: 'never',
        // Keep the overlay out of the remembered filter so it never persists across sessions.
        overlay: 'never',
        targetGroupIdentifier: 'never',
        txRefs: 'untilChanged',
      },
      tableId: TableId.HISTORY,
    },
    request: {
      cancelTag: GROUPS_CANCEL_TAG,
    },
    urlState: routeWhen(mainPage),
  });

  const locations = computed<string[]>(() => {
    const filteredData = get(filters);

    if ('location' in filteredData) {
      if (typeof filteredData.location === 'string')
        return [filteredData.location];
      else if (Array.isArray(filteredData.location))
        return filteredData.location;

      return [];
    }
    return [];
  });

  const { highlightedGroupIdentifier, highlightedIdentifiers, highlightTypes } = useHistoryEventHighlights();

  const includes = computed<{ evmEvents: boolean; onlineEvents: boolean }>(() => {
    const entryTypesValue = toValue(entryTypes);
    return {
      evmEvents: entryTypesValue ? entryTypesValue.some(type => isEvmEventType(type)) : true,
      onlineEvents: entryTypesValue ? entryTypesValue.some(type => isOnlineHistoryEventType(type)) : true,
    };
  });

  const hasActiveFiltersRaw = computed<boolean>(() =>
    Object.keys(get(filters)).length > 0
    || get(locationLabels).length > 0
    || !isEqual(get(toggles), getDefaultToggles()));

  const hasActiveFilters = useRefWithDebounce(hasActiveFiltersRaw, 500);

  function clearFilters(): void {
    setFilter({});
    onLocationLabelsChanged([]);
    set(toggles, { ...getDefaultToggles() });
  }

  function onLocationLabelsChanged(labels: string[]): void {
    // locationLabels feeds both a request source and a url source, so the table
    // cannot see this as an interaction on its own. Attribute it explicitly or the
    // new labels never reach the URL.
    markUserIntent();
    set(locationLabels, labels);
  }

  /**
   * Clear highlights when the user changes page or filters.
   * Sort changes (orderByAttributes, ascending) are excluded so highlights
   * persist through reordering.
   */
  watch(requestPayload, (params, oldParams) => {
    if (!oldParams || !get(shouldPreserveHighlights) || get(isNavigating))
      return;

    const current = objectOmit(params, ['orderByAttributes', 'ascending']);
    const previous = objectOmit(oldParams, ['orderByAttributes', 'ascending']);

    if (isEqual(current, previous))
      return;

    set(shouldPreserveHighlights, false);
    clearAllHighlightTargets();
  }, { deep: true });

  /** Re-enable highlight preservation when new highlight params arrive via navigation. */
  watch(() => get(route).query, (query, oldQuery) => {
    if (highlightKeys.some(key => query[key] && query[key] !== oldQuery?.[key]))
      set(shouldPreserveHighlights, true);
  });

  return {
    clearFilters,
    duplicateHandlingStatus: duplicateHandlingStatusFromQuery,
    filters,
    groupIdentifiers: groupIdentifiersFromQuery,
    groupLoading,
    groups,
    hasActiveFilters,
    highlightedGroupIdentifier,
    highlightedIdentifiers,
    highlightTypes,
    identifiers: missingAcquisitionFromQuery,
    includes,
    locationLabels: shallowReadonly(locationLabels),
    locations,
    matchers,
    onLocationLabelsChanged,
    pagination,
    refetch,
    requestPayload,
    setFilter,
    setPage,
    sort,
    usedLocationLabels,
  };
}
