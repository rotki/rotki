import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventsToggles } from '@/components/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { Collection } from '@/types/collection';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { type Account, type HistoryEventEntryType, toSnakeCase, type Writeable } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { type Filters, type Matcher, useHistoryEventFilter } from '@/composables/filters/events';
import { useHistoryEvents } from '@/composables/history/events';
import { isValidHistoryEventState } from '@/composables/history/events/mapping/state';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { TableId } from '@/modules/table/use-remember-table-sorting';
import { RouterLocationLabelsSchema } from '@/types/route';
import {
  isEvmEventType,
  isOnlineHistoryEventType,
} from '@/utils/history/events';

type Period = { fromTimestamp?: string; toTimestamp?: string } | { fromTimestamp?: number; toTimestamp?: number };

export const DuplicateHandlingStatus = {
  AUTO_FIX: 'auto-fix',
  MANUAL_REVIEW: 'manual-review',
} as const;

export type DuplicateHandlingStatus = (typeof DuplicateHandlingStatus)[keyof typeof DuplicateHandlingStatus];

interface HistoryEventsFiltersOptions {
  entryTypes: Ref<HistoryEventEntryType[] | undefined>;
  eventSubTypes: Ref<string[]>;
  eventTypes: Ref<string[]>;
  externalAccountFilter: Ref<Account[]>;
  location: Ref<string | undefined>;
  mainPage: Ref<boolean>;
  period: Ref<Period | undefined>;
  protocols: Ref<string[]>;
  useExternalAccountFilter: Ref<boolean | undefined>;
  validators: Ref<number[] | undefined>;
}

interface UseHistoryEventsFiltersReturn {
  duplicateHandlingStatus: ComputedRef<DuplicateHandlingStatus | undefined>;
  locationLabels: Ref<string[]>;
  groupIdentifiers: ComputedRef<string[] | undefined>;
  fetchData: () => Promise<void>;
  filters: ComputedRef<Filters>;
  groupLoading: Ref<boolean>;
  groups: Ref<Collection<HistoryEventRow>>;
  highlightedIdentifiers: ComputedRef<string[] | undefined>;
  identifiers: ComputedRef<string[] | undefined>;
  includes: ComputedRef<{ evmEvents: boolean; onlineEvents: boolean }>;
  locationOverview: Ref<string | undefined>;
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
  const locationOverview = ref(get(location));

  const route = useRoute();
  const { fetchHistoryEvents } = useHistoryEvents();

  // Define these early since they're used in extraParams
  const identifiersFromQuery = computed<string[] | undefined>(() => {
    const { identifiers } = get(route).query;
    return identifiers ? [identifiers as string] : undefined;
  });

  const groupIdentifiersFromQuery = computed<string[] | undefined>(() => {
    const { groupIdentifiers } = get(route).query;
    if (!groupIdentifiers)
      return undefined;

    const ids = groupIdentifiers as string;
    return ids.includes(',') ? ids.split(',') : [ids];
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
    if (isDefined(useExternalAccountFilter))
      return get(externalAccountFilter).map(account => account.address);

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
  >(fetchHistoryEvents, {
    defaultParams: computed(() => {
      if (isDefined(entryTypes) && get(entryTypes)) {
        return {
          entryTypes: {
            values: get(entryTypes) || [],
          },
        };
      }
      return {};
    }),
    extraParams: computed(() => {
      const stateMarkers = get(toggles, 'stateMarkers');
      return {
        excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
        groupIdentifiers: get(groupIdentifiersFromQuery),
        identifiers: get(identifiersFromQuery),
        ...(stateMarkers.length > 0 ? { stateMarkers } : {}),
      };
    }),
    filterSchema: () => useHistoryEventFilter({
      eventSubtypes: (get(eventSubTypes) || []).length > 0,
      eventTypes: (get(eventTypes) || []).length > 0,
      locations: !!get(location),
      period: !!get(period),
      protocols: (get(protocols) || []).length > 0,
      validators: !!get(validators),
    }, entryTypes),
    history: get(mainPage) ? 'router' : false,
    onUpdateFilters(query) {
      const parsedLocationLabels = RouterLocationLabelsSchema.parse(query);
      const locationLabelsParsed = parsedLocationLabels.locationLabels;
      if (!locationLabelsParsed || locationLabelsParsed.length === 0)
        set(locationLabels, []);
      else
        set(locationLabels, locationLabelsParsed);

      const stateMarkersParam = query.stateMarkers;
      if (stateMarkersParam && typeof stateMarkersParam === 'string') {
        set(toggles, {
          ...get(toggles),
          stateMarkers: stateMarkersParam.split(',').filter(isValidHistoryEventState),
        });
      }
    },
    persistFilter: computed(() => ({
      enabled: true,
      excludeKeys: ['identifiers', 'groupIdentifiers', 'duplicateHandlingStatus'],
      tableId: TableId.HISTORY,
      transientKeys: ['txRefs'],
    })),
    queryParamsOnly: computed(() => {
      const duplicateHandlingStatusValue = get(duplicateHandlingStatusFromQuery);
      const groupIdentifiersValue = get(groupIdentifiersFromQuery);

      const stateMarkersValue = get(toggles, 'stateMarkers');
      return {
        duplicateHandlingStatus: duplicateHandlingStatusValue,
        groupIdentifiers: groupIdentifiersValue?.join(','),
        locationLabels: get(usedLocationLabels),
        ...(stateMarkersValue.length > 0 ? { stateMarkers: stateMarkersValue.join(',') } : {}),
      };
    }),
    requestParams: computed<Partial<HistoryEventRequestPayload>>(() => {
      const params: Writeable<Partial<HistoryEventRequestPayload>> = {
        aggregateByGroupIds: true,
        counterparties: get(protocols),
        eventSubtypes: get(eventSubTypes),
        eventTypes: get(eventTypes),
      };

      const accountsValue = get(usedLocationLabels);

      if (isDefined(locationOverview))
        params.location = toSnakeCase(get(locationOverview));

      if (accountsValue.length > 0)
        params.locationLabels = get(usedLocationLabels);

      if (isDefined(period)) {
        const { fromTimestamp, toTimestamp } = get(period);
        params.fromTimestamp = fromTimestamp;
        params.toTimestamp = toTimestamp;
      }

      if (isDefined(validators) && get(validators))
        params.validatorIndices = get(validators)?.map(v => v.toString()) || [];

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
    const { highlightedIdentifier, negativeBalanceEvent } = get(route).query;
    const identifier = highlightedIdentifier ?? negativeBalanceEvent;
    return identifier ? [identifier as string] : undefined;
  });

  const includes = computed<{ evmEvents: boolean; onlineEvents: boolean }>(() => {
    const entryTypesValue = get(entryTypes);
    return {
      evmEvents: entryTypesValue ? entryTypesValue.some(type => isEvmEventType(type)) : true,
      onlineEvents: entryTypesValue ? entryTypesValue.some(type => isOnlineHistoryEventType(type)) : true,
    };
  });

  function onLocationLabelsChanged(labels: string[]): void {
    set(userAction, true);
    set(locationLabels, labels);
  }

  watchDebounced([filters, locationLabels], ([filters, locationLabels], [oldFilters, oldLocationLabels]) => {
    const filterChanged = !isEqual(filters, oldFilters);
    const accountsChanged = !isEqual(locationLabels, oldLocationLabels);

    if (!(filterChanged || accountsChanged))
      return;

    // Update locationOverview when filter location changes
    if (filterChanged)
      set(locationOverview, filters.location);

    // When accounts change, trigger a filter update to force re-fetch with new location labels
    // The setPage(1) is handled by usePaginationFilters watch on [filters, extraParams]
    if (accountsChanged && get(usedLocationLabels).length > 0) {
      const updatedFilter = { ...get(filters) };
      updateFilter(updatedFilter);
    }
  }, { debounce: 100 });

  return {
    duplicateHandlingStatus: duplicateHandlingStatusFromQuery,
    fetchData,
    filters,
    groupIdentifiers: groupIdentifiersFromQuery,
    groupLoading,
    groups,
    highlightedIdentifiers,
    identifiers: identifiersFromQuery,
    includes,
    locationLabels,
    locationOverview,
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
