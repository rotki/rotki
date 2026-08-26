import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { WritableRef } from '@/modules/core/common/common-types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { isEqual } from 'es-toolkit';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';
import { type ChangeSource, routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';
import {
  isEvmEventType,
  isOnlineHistoryEventType,
} from '@/modules/history/event-utils';
import { DuplicateHandlingStatus, type HighlightType } from '@/modules/history/events/action-types';
import { buildHistoryEventSources } from '@/modules/history/events/history-event-query';
import { type HistoryEventsRestrictions, toRestrictionGetters } from '@/modules/history/events/history-events-restrictions';
import { useHistoryEventHighlights, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

/**
 * The payload without its sorting, so a re-sort is not read as a change of what is being asked for.
 * Written out rather than pulled from a helper: this file is at the dependency cap.
 */
function withoutSorting(
  { ascending, orderByAttributes, ...rest }: HistoryEventRequestPayload,
): Partial<HistoryEventRequestPayload> {
  return rest;
}

interface HistoryEventsFiltersOptions {
  /**
   * The pill-bar fields, and the filter bag they are bound to. Both are built by the view: the
   * fields read the bag to scope their option lists, and the table reads the url shape of the bag
   * (and the keys the request wraps as `{ behaviour, values }`) off the fields, so the bag has to
   * exist before either.
   */
  fields: MaybeRefOrGetter<FieldDef[]>;
  filters: Ref<Filters>;
  mainPage: MaybeRefOrGetter<boolean>;
  /** What the view fixes; the same bag the pill bar reads. */
  restrictions: MaybeRefOrGetter<HistoryEventsRestrictions>;
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
  /** The selected action verb, if any; the bar's `action` param pill both reads and drives it. */
  action: Readonly<Ref<string | undefined>>;
  onActionChanged: (verbKey: string | undefined) => void;
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
  // Written back by applyHistoryEventRouteQuery (history-event-query.ts) when the overlay is
  // restored from the route, so it cannot be widened to MaybeRefOrGetter.
  overlayMode: WritableRef<OverlayMode> = ref<OverlayMode>(OverlayMode.NONE),
): UseHistoryEventsFiltersReturn {
  const { fields, filters: modelFilters, mainPage } = options;
  const {
    entryTypes,
    eventTypes,
    externalAccounts,
    location,
    period,
    protocols,
    validators,
  } = toRestrictionGetters(options.restrictions);

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
    return typeof missingAcquisitionIdentifier === 'string' && missingAcquisitionIdentifier.length > 0
      ? [missingAcquisitionIdentifier]
      : undefined;
  });

  const groupIdentifiersRaw = computed<string | undefined>(() => {
    const { groupIdentifiers } = get(route).query;
    return typeof groupIdentifiers === 'string' && groupIdentifiers.length > 0 ? groupIdentifiers : undefined;
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

  // A view that selects accounts for the user owns this axis outright, so its (possibly empty) set
  // replaces the bar's, rather than being merged with it.
  const usedLocationLabels = computed<string[]>(() => {
    const pinned = externalAccounts();
    return pinned ? pinned.map(account => account.address) : get(locationLabels);
  });

  // Owned here rather than by the caller: it is written back from the route like locationLabels,
  // and expanded into the request by the source that already owns the two event-type keys.
  const action = ref<string>();

  const sources = buildHistoryEventSources({
    action,
    duplicateHandlingStatusFromQuery,
    entryTypes,
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
    Filters
  >({
    fetch: fetchHistoryEventsTagged,
    fields,
    filters: modelFilters,
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
    const entryTypesValue = entryTypes();
    return {
      evmEvents: entryTypesValue ? entryTypesValue.some(type => isEvmEventType(type)) : true,
      onlineEvents: entryTypesValue ? entryTypesValue.some(type => isOnlineHistoryEventType(type)) : true,
    };
  });

  const hasActiveFiltersRaw = computed<boolean>(() =>
    Object.keys(get(filters)).length > 0
    || get(locationLabels).length > 0
    || get(action) !== undefined
    || !isEqual(get(toggles), getDefaultToggles()));

  const hasActiveFilters = useRefWithDebounce(hasActiveFiltersRaw, 500);

  function clearFilters(): void {
    setFilter({});
    onLocationLabelsChanged([]);
    onActionChanged(undefined);
    set(toggles, { ...getDefaultToggles() });
  }

  function onActionChanged(verbKey: string | undefined): void {
    // Same as locationLabels below: it drives a request source and a url source, so the change has
    // to be attributed explicitly or it never reaches the URL.
    markUserIntent();
    set(action, verbKey);
  }

  /**
   * Applies a change to the selected accounts.
   *
   * @remarks
   * The intent has to be marked by hand: `locationLabels` feeds both a request and a url source,
   * so the table cannot recognise this as an interaction and the new labels never reach the URL.
   */
  function onLocationLabelsChanged(labels: string[]): void {
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

    const current = withoutSorting(params);
    const previous = withoutSorting(oldParams);

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
    action: shallowReadonly(action),
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
    onActionChanged,
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
