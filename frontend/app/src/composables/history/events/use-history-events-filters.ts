import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { type Account, type HistoryEventEntryType, toSnakeCase, type Writeable } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { type Filters, type Matcher, useHistoryEventFilter } from '@/composables/filters/events';
import { useHistoryEvents } from '@/composables/history/events';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { RouterAccountsSchema } from '@/types/route';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import {
  isEvmEventType,
  isOnlineHistoryEventType,
} from '@/utils/history/events';

type Period = { fromTimestamp?: string; toTimestamp?: string } | { fromTimestamp?: number; toTimestamp?: number };

interface HistoryEventsFiltersOptions {
  entryTypes?: Ref<HistoryEventEntryType[] | undefined>;
  eventSubTypes?: Ref<string[]>;
  eventTypes?: Ref<string[]>;
  externalAccountFilter?: Ref<Account[]>;
  location?: Ref<string | undefined>;
  mainPage?: Ref<boolean>;
  period?: Ref<Period | undefined>;
  protocols?: Ref<string[]>;
  useExternalAccountFilter?: Ref<boolean | undefined>;
  validators?: Ref<number[] | undefined>;
  eventIdentifiers?: Ref<string[] | undefined>;
  identifiers?: Ref<string[] | undefined>;
}

interface UseHistoryEventsFiltersReturn {
  accounts: Ref<BlockchainAccount<AddressData>[]>;
  eventIdentifiers: ComputedRef<string[] | undefined>;
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
  onFilterAccountsChanged: (acc: BlockchainAccount<AddressData>[]) => void;
  pageParams: ComputedRef<HistoryEventRequestPayload>;
  pagination: ComputedRef<TablePaginationData>;
  setPage: (page: number, action?: boolean) => void;
  sort: ComputedRef<DataTableSortData<HistoryEventRow>>;
  updateFilter: (newFilter: Filters) => void;
  usedAccounts: ComputedRef<Account[]>;
  userAction: Ref<boolean>;
}

export function useHistoryEventsFilters(
  options: HistoryEventsFiltersOptions,
  toggles: Ref<{
    customizedEventsOnly: boolean;
    showIgnoredAssets: boolean;
    matchExactEvents: boolean;
  }>,
  _fetchDataCallback: () => Promise<void>,
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

  const accounts = ref<BlockchainAccount<AddressData>[]>([]);
  const locationOverview = ref(get(location));

  const route = useRoute();
  const { fetchHistoryEvents } = useHistoryEvents();
  const { getAccountByAddress } = useBlockchainAccountsStore();

  const usedAccounts = computed<Account[]>(() => {
    if (isDefined(useExternalAccountFilter) && get(externalAccountFilter))
      return get(externalAccountFilter) || [];

    const accountData = get(accounts).map(account => ({
      address: getAccountAddress(account),
      chain: account.chain,
    }));
    return accountData.length > 0 ? [accountData[0]] : accountData;
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
    extraParams: computed(() => ({
      customizedEventsOnly: get(toggles, 'customizedEventsOnly'),
      eventIdentifiers: get(eventIdentifiersFromQuery),
      excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
      identifiers: get(identifiersFromQuery),
    })),
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
      const parsedAccounts = RouterAccountsSchema.parse(query);
      const accountsParsed = parsedAccounts.accounts;
      if (!accountsParsed || accountsParsed.length === 0)
        set(accounts, []);
      else
        set(accounts, accountsParsed.map(({ address, chain }) => getAccountByAddress(address, chain)));
    },
    queryParamsOnly: computed(() => ({
      accounts: get(usedAccounts).map(account => `${account.address}#${account.chain}`),
    })),
    requestParams: computed<Partial<HistoryEventRequestPayload>>(() => {
      const params: Writeable<Partial<HistoryEventRequestPayload>> = {
        counterparties: get(protocols),
        eventSubtypes: get(eventSubTypes),
        eventTypes: get(eventTypes),
        groupByEventIds: true,
      };

      const accountsValue = get(usedAccounts);

      if (isDefined(locationOverview))
        params.location = toSnakeCase(get(locationOverview));

      if (accountsValue.length > 0)
        params.locationLabels = accountsValue.map(account => account.address);

      if (isDefined(period) && get(period)) {
        const periodValue = get(period);
        if (periodValue) {
          params.fromTimestamp = periodValue.fromTimestamp;
          params.toTimestamp = periodValue.toTimestamp;
        }
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

  const identifiersFromQuery = computed<string[] | undefined>(() => {
    const { identifiers } = get(route).query;
    return identifiers ? [identifiers as string] : undefined;
  });

  const eventIdentifiersFromQuery = computed<string[] | undefined>(() => {
    const { eventIdentifiers } = get(route).query;
    return eventIdentifiers ? [eventIdentifiers as string] : undefined;
  });

  const highlightedIdentifiers = computed<string[] | undefined>(() => {
    const { highlightedIdentifier } = get(route).query;
    return highlightedIdentifier ? [highlightedIdentifier as string] : undefined;
  });

  const includes = computed<{ evmEvents: boolean; onlineEvents: boolean }>(() => {
    const entryTypesValue = get(entryTypes);
    return {
      evmEvents: entryTypesValue ? entryTypesValue.some(type => isEvmEventType(type)) : true,
      onlineEvents: entryTypesValue ? entryTypesValue.some(type => isOnlineHistoryEventType(type)) : true,
    };
  });

  function onFilterAccountsChanged(acc: BlockchainAccount<AddressData>[]): void {
    set(userAction, true);
    set(accounts, acc.length > 0 ? [acc[0]] : []);
  }

  // Watch filters and accounts changes
  watch([filters, usedAccounts], ([filters, usedAccounts], [oldFilters, oldAccounts]) => {
    const filterChanged = !isEqual(filters, oldFilters);
    const accountsChanged = !isEqual(usedAccounts, oldAccounts);

    if (!(filterChanged || accountsChanged))
      return;

    if (accountsChanged && usedAccounts.length > 0) {
      const updatedFilter = { ...get(filters) };
      updateFilter(updatedFilter);
    }

    if (filterChanged || accountsChanged) {
      set(locationOverview, filters.location);
      setPage(1);
    }
  });

  return {
    accounts,
    eventIdentifiers: eventIdentifiersFromQuery,
    fetchData,
    filters,
    groupLoading,
    groups,
    highlightedIdentifiers,
    identifiers: identifiersFromQuery,
    includes,
    locationOverview,
    locations,
    matchers,
    onFilterAccountsChanged,
    pageParams,
    pagination,
    setPage,
    sort,
    updateFilter,
    usedAccounts,
    userAction,
  };
}
