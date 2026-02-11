import type { ContextColorsType, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRef, Ref } from 'vue';
import type { HistoryEventsToggles } from '@/components/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { Collection } from '@/types/collection';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { type Account, type HistoryEventEntryType, toSnakeCase, type Writeable } from '@rotki/common';
import { startPromise } from '@shared/utils';
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

export { useHistoryEventNavigationConsumer } from '@/composables/history/events/use-history-event-navigation';

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

export type HighlightType = ContextColorsType;

export const HIGHLIGHT_CLASSES: Partial<Record<HighlightType, string>> = {
  error: '!bg-rui-error/15',
  success: '!bg-rui-success/15',
  warning: '!bg-rui-warning/15',
};

export function getHighlightClass(highlightType?: HighlightType): string | undefined {
  if (!highlightType)
    return undefined;
  return HIGHLIGHT_CLASSES[highlightType];
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
  highlightTypes: ComputedRef<Record<string, HighlightType>>;
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

  const GROUPS_CANCEL_TAG = 'history-events-groups';

  const route = useRoute();
  const router = useRouter();
  const { fetchHistoryEvents } = useHistoryEvents();

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
  >(fetchHistoryEventsTagged, {
    cancelTag: GROUPS_CANCEL_TAG,
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
    fetchDebounce: 200,
    extraParams: computed(() => {
      const stateMarkers = get(toggles, 'stateMarkers');
      return {
        excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
        groupIdentifiers: get(groupIdentifiersFromQuery),
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
      const { highlightedAssetMovement, highlightedPotentialMatch, highlightedNegativeBalanceEvent } = get(route).query;

      const missingAcquisitionValue = get(missingAcquisitionFromQuery);
      const stateMarkersValue = get(toggles, 'stateMarkers');
      return {
        duplicateHandlingStatus: duplicateHandlingStatusValue,
        groupIdentifiers: groupIdentifiersValue?.join(','),
        highlightedAssetMovement,
        highlightedNegativeBalanceEvent,
        highlightedPotentialMatch,
        locationLabels: get(usedLocationLabels),
        missingAcquisitionIdentifier: missingAcquisitionValue?.join(','),
        ...(stateMarkersValue.length > 0 ? { stateMarkers: stateMarkersValue.join(',') } : {}),
      };
    }),
    requestParams: computed<Partial<HistoryEventRequestPayload>>(() => {
      const params: Writeable<Partial<HistoryEventRequestPayload>> = {
        aggregateByGroupIds: true,
        counterparties: get(protocols),
        eventSubtypes: get(eventSubTypes),
        eventTypes: get(eventTypes),
        identifiers: get(missingAcquisitionFromQuery),
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

  const highlightTypes = computed<Record<string, HighlightType>>(() => {
    const { highlightedAssetMovement, highlightedPotentialMatch, highlightedNegativeBalanceEvent } = get(route).query;
    const types: Record<string, HighlightType> = {};

    if (highlightedAssetMovement)
      types[highlightedAssetMovement.toString()] = 'warning';
    if (highlightedNegativeBalanceEvent)
      types[highlightedNegativeBalanceEvent.toString()] = 'error';
    if (highlightedPotentialMatch)
      types[highlightedPotentialMatch.toString()] = 'success';

    return types;
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

    // Clear highlight when non-pagination filters change
    const { highlightedAssetMovement, highlightedNegativeBalanceEvent, highlightedPotentialMatch, ...remainingQuery } = get(route).query;
    if (highlightedAssetMovement || highlightedPotentialMatch || highlightedNegativeBalanceEvent) {
      startPromise(router.replace({
        query: remainingQuery,
      }));
    }

    // Update locationOverview when filter location changes
    if (filterChanged)
      set(locationOverview, filters.location);
  }, { debounce: 100 });

  return {
    duplicateHandlingStatus: duplicateHandlingStatusFromQuery,
    fetchData,
    filters,
    groupIdentifiers: groupIdentifiersFromQuery,
    groupLoading,
    groups,
    highlightedIdentifiers,
    highlightTypes,
    identifiers: missingAcquisitionFromQuery,
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
