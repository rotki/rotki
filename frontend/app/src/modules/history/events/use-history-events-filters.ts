import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { type Account, type HistoryEventEntryType, toSnakeCase, type Writeable } from '@rotki/common';
import { objectOmit } from '@vueuse/shared';
import { isEqual } from 'es-toolkit';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { type Filters, type Matcher, useHistoryEventFilter } from '@/modules/core/table/filters/use-events-filter';
import { RouterLocationLabelsSchema } from '@/modules/core/table/route';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';
import {
  isEvmEventType,
  isOnlineHistoryEventType,
} from '@/modules/history/event-utils';
import { DuplicateHandlingStatus, type HighlightType } from '@/modules/history/events/action-types';
import { isValidHistoryEventState } from '@/modules/history/events/mapping/use-history-event-state-mapping';
import { HIGHLIGHT_FETCH_DEBOUNCE, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';
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
  locationLabels: Ref<string[]>;
  groupIdentifiers: ComputedRef<string[] | undefined>;
  fetchData: () => Promise<void>;
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
  pageParams: ComputedRef<HistoryEventRequestPayload>;
  pagination: ComputedRef<TablePaginationData>;
  setPage: (page: number, action?: boolean) => void;
  sort: ComputedRef<DataTableSortData<HistoryEventRow>>;
  updateFilter: (newFilter: Filters) => void;
  usedLocationLabels: ComputedRef<string[]>;
  userAction: Ref<boolean>;
}

export function useHistoryEventsFilters(
  options: HistoryEventsFiltersOptions,
  toggles: Ref<HistoryEventsToggles>,
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

  const highlightKeys = ['highlightedAssetMovement', 'highlightedInternalTxConflict', 'highlightedPotentialMatch', 'highlightedNegativeBalanceEvent'] as const;
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

  const {
    fetchData,
    filters,
    isLoading: groupLoading,
    matchers,
    pageParams,
    pagination,
    setPage,
    sort,
    state: groups,
    updateFilter,
    userAction,
  } = usePaginationFilters<
    HistoryEventRow,
    HistoryEventRequestPayload,
    Filters,
    Matcher
  >(fetchHistoryEventsTagged, {
    cancelTag: GROUPS_CANCEL_TAG,
    defaultParams: computed(() => {
      if (toValue(entryTypes) !== undefined && toValue(entryTypes)) {
        return {
          entryTypes: {
            values: toValue(entryTypes) || [],
          },
        };
      }
      return {};
    }),
    fetchDebounce: HIGHLIGHT_FETCH_DEBOUNCE,
    extraParams: computed(() => {
      const stateMarkers = get(toggles, 'stateMarkers');
      return {
        excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
        groupIdentifiers: get(groupIdentifiersFromQuery),
        ...(stateMarkers.length > 0 ? { stateMarkers } : {}),
      };
    }),
    filterSchema: () => useHistoryEventFilter({
      eventSubtypes: (toValue(eventSubTypes) || []).length > 0,
      eventTypes: (toValue(eventTypes) || []).length > 0,
      locations: !!toValue(location),
      period: !!toValue(period),
      protocols: (toValue(protocols) || []).length > 0,
      validators: !!toValue(validators),
    }, computed<HistoryEventEntryType[] | undefined>(() => toValue(entryTypes))),
    history: toValue(mainPage) ? 'router' : false,
    onUpdateFilters(query) {
      const parsedLocationLabels = RouterLocationLabelsSchema.parse(query);
      const locationLabelsParsed = parsedLocationLabels.locationLabels;
      if (!locationLabelsParsed || locationLabelsParsed.length === 0)
        set(locationLabels, []);
      else
        set(locationLabels, locationLabelsParsed);

      const stateMarkersParam = query.stateMarkers;
      set(toggles, {
        ...get(toggles),
        stateMarkers: stateMarkersParam && typeof stateMarkersParam === 'string'
          ? stateMarkersParam.split(',').filter(isValidHistoryEventState)
          : [],
      });
    },
    persistFilter: computed(() => ({
      enabled: true,
      excludeKeys: [
        'missingAcquisitionIdentifier',
        'groupIdentifiers',
        'duplicateHandlingStatus',
        'targetGroupIdentifier',
        'highlightedAssetMovement',
        'highlightedInternalTxConflict',
        'highlightedPotentialMatch',
        'highlightedNegativeBalanceEvent',
      ],
      tableId: TableId.HISTORY,
      transientKeys: ['txRefs'],
    })),
    // Query params that should be preserved in the URL but not used for API requests.
    queryParamsOnly: computed(() => {
      const duplicateHandlingStatusValue = get(duplicateHandlingStatusFromQuery);
      const groupIdentifiersValue = get(groupIdentifiersFromQuery);
      const preserve = get(shouldPreserveHighlights);
      const { highlightedAssetMovement, highlightedInternalTxConflict, highlightedPotentialMatch, highlightedNegativeBalanceEvent } = get(route).query;

      const missingAcquisitionValue = get(missingAcquisitionFromQuery);
      const stateMarkersValue = get(toggles, 'stateMarkers');
      return {
        duplicateHandlingStatus: duplicateHandlingStatusValue,
        groupIdentifiers: groupIdentifiersValue?.join(','),
        ...(preserve
          ? {
              highlightedAssetMovement,
              highlightedInternalTxConflict,
              highlightedNegativeBalanceEvent,
              highlightedPotentialMatch,
            }
          : {}),
        locationLabels: get(usedLocationLabels),
        missingAcquisitionIdentifier: missingAcquisitionValue?.join(','),
        ...(stateMarkersValue.length > 0 ? { stateMarkers: stateMarkersValue.join(',') } : {}),
      };
    }),
    requestParams: computed<Partial<HistoryEventRequestPayload>>(() => {
      const params: Writeable<Partial<HistoryEventRequestPayload>> = {
        aggregateByGroupIds: true,
        counterparties: toValue(protocols),
        eventSubtypes: toValue(eventSubTypes),
        eventTypes: toValue(eventTypes),
        identifiers: get(missingAcquisitionFromQuery),
      };

      const accountsValue = get(usedLocationLabels);

      const locationVal = toValue(location);
      if (locationVal !== undefined)
        params.location = toSnakeCase(locationVal);

      if (accountsValue.length > 0)
        params.locationLabels = get(usedLocationLabels);

      const periodVal = toValue(period);
      if (periodVal !== undefined) {
        const { fromTimestamp, toTimestamp } = periodVal;
        params.fromTimestamp = fromTimestamp;
        params.toTimestamp = toTimestamp;
      }

      const validatorsVal = toValue(validators);
      if (validatorsVal !== undefined && validatorsVal)
        params.validatorIndices = validatorsVal.map(v => v.toString()) || [];

      return params;
    }),
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

  const highlightedIdentifiers = computed<string[] | undefined>(() => {
    const { highlightedAssetMovement, highlightedPotentialMatch, highlightedNegativeBalanceEvent } = get(route).query;
    const identifiers: string[] = [];
    if (highlightedAssetMovement)
      identifiers.push(highlightedAssetMovement.toString());
    if (highlightedPotentialMatch)
      identifiers.push(highlightedPotentialMatch.toString());
    if (highlightedNegativeBalanceEvent)
      identifiers.push(highlightedNegativeBalanceEvent.toString());
    return identifiers.length > 0 ? identifiers : undefined;
  });
  const highlightedGroupIdentifier = computed<string | undefined>(() => {
    const { highlightedInternalTxConflict } = get(route).query;
    return highlightedInternalTxConflict ? highlightedInternalTxConflict.toString() : undefined;
  });
  const highlightTypes = computed<Record<string, HighlightType>>(() => {
    const { highlightedAssetMovement, highlightedPotentialMatch, highlightedNegativeBalanceEvent } = get(route).query;
    const types: Record<string, HighlightType> = {};
    if (highlightedAssetMovement)
      types[highlightedAssetMovement.toString()] = 'warning';
    if (highlightedNegativeBalanceEvent)
      types[highlightedNegativeBalanceEvent.toString()] = 'error';
    if (highlightedPotentialMatch)
      types[highlightedPotentialMatch.toString()] = 'success';
    const groupId = get(highlightedGroupIdentifier);
    if (groupId)
      types[`group:${groupId}`] = 'warning';
    return types;
  });
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
    updateFilter({});
    onLocationLabelsChanged([]);
    set(toggles, { ...getDefaultToggles() });
  }

  function onLocationLabelsChanged(labels: string[]): void {
    set(userAction, true);
    set(locationLabels, labels);
  }

  /**
   * Clear highlights when the user changes page or filters.
   * Sort changes (orderByAttributes, ascending) are excluded so highlights
   * persist through reordering.
   */
  watch(pageParams, (params, oldParams) => {
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
    fetchData,
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
    locationLabels,
    locations,
    matchers,
    onLocationLabelsChanged,
    pageParams,
    pagination,
    setPage,
    sort,
    updateFilter,
    usedLocationLabels,
    userAction,
  };
}
