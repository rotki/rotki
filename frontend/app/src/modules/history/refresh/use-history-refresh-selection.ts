import type { ComputedRef, Ref } from 'vue';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import type { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';

export const HistoryRefreshTab = {
  CHAINS: 'chains',
  EVENTS: 'events',
  EXCHANGES: 'exchanges',
  PROTOCOLS: 'protocols',
} as const;

export type HistoryRefreshTab = typeof HistoryRefreshTab[keyof typeof HistoryRefreshTab];

interface TabState {
  /** How many entries the tab currently has picked. */
  count: ComputedRef<number>;
  /** Whether the tab reported that its picks cover everything it offers. */
  allSelected: Ref<boolean>;
}

interface UseHistoryRefreshSelectionReturn {
  /** All bound with `v-model`, so they stay writable. */
  modelTab: Ref<HistoryRefreshTab>;
  modelSearch: Ref<string>;
  modelSelectedChain: Ref<string | undefined>;
  modelSelectedAccounts: Ref<ChainAddress[]>;
  modelSelectedExchanges: Ref<Exchange[]>;
  modelSelectedQueries: Ref<OnlineHistoryEventsQueryType[]>;
  modelSelectedProtocolQueries: Ref<OnlineHistoryEventsQueryType[]>;
  /** How a tab reports that its picks cover everything it offers. */
  setAllSelected: (tab: HistoryRefreshTab, allSelected: boolean) => void;
  /** Some, but not all, of what the active tab offers is picked. */
  indeterminate: ComputedRef<boolean>;
  /** Everything the active tab offers is picked. */
  selected: ComputedRef<boolean>;
  totalSelected: ComputedRef<number>;
  searchLabel: ComputedRef<string>;
  typeText: ComputedRef<string>;
  /** The active tab's picks, in the shape the parent refreshes by. */
  getRefreshPayload: () => HistoryRefreshEventData;
  reset: () => void;
}

/**
 * The picks behind the history refresh menu.
 *
 * Each of the four tabs keeps its own selection and reports back whether that selection covers
 * everything it offers, which is what the "select all" checkbox and the refresh button read. The
 * tabs are independent on purpose: switching tabs resets, because a selection made against one
 * tab's entries says nothing about another's.
 */
export function useHistoryRefreshSelection(): UseHistoryRefreshSelectionReturn {
  const { t } = useI18n({ useScope: 'global' });

  const modelTab = shallowRef<HistoryRefreshTab>(HistoryRefreshTab.CHAINS);
  const modelSearch = shallowRef<string>('');

  const modelSelectedChain = shallowRef<string>();
  const modelSelectedAccounts = ref<ChainAddress[]>([]);
  const allAccountsSelected = shallowRef<boolean>(false);

  const modelSelectedExchanges = ref<Exchange[]>([]);
  const allExchangesSelected = shallowRef<boolean>(false);

  const modelSelectedQueries = ref<OnlineHistoryEventsQueryType[]>([]);
  const allQueriesSelected = shallowRef<boolean>(false);

  const modelSelectedProtocolQueries = ref<OnlineHistoryEventsQueryType[]>([]);
  const allProtocolQueriesSelected = shallowRef<boolean>(false);

  const tabStates: Record<HistoryRefreshTab, TabState> = {
    [HistoryRefreshTab.CHAINS]: {
      allSelected: allAccountsSelected,
      count: computed<number>(() => get(modelSelectedAccounts).length),
    },
    [HistoryRefreshTab.EVENTS]: {
      allSelected: allQueriesSelected,
      count: computed<number>(() => get(modelSelectedQueries).length),
    },
    [HistoryRefreshTab.EXCHANGES]: {
      allSelected: allExchangesSelected,
      count: computed<number>(() => get(modelSelectedExchanges).length),
    },
    [HistoryRefreshTab.PROTOCOLS]: {
      allSelected: allProtocolQueriesSelected,
      count: computed<number>(() => get(modelSelectedProtocolQueries).length),
    },
  };

  const activeTabState = computed<TabState>(() => tabStates[get(modelTab)]);

  const totalSelected = computed<number>(() => get(get(activeTabState).count));

  const indeterminate = computed<boolean>(
    () => get(totalSelected) > 0 && !get(get(activeTabState).allSelected),
  );

  const selected = computed<boolean>(
    () => get(totalSelected) > 0 && get(get(activeTabState).allSelected),
  );

  const searchLabel = computed<string>(() => {
    switch (get(modelTab)) {
      case HistoryRefreshTab.CHAINS:
        return isDefined(modelSelectedChain)
          ? t('history_refresh_selection.search_address')
          : t('history_refresh_selection.search_chain');
      case HistoryRefreshTab.EXCHANGES:
        return t('history_refresh_selection.search_exchanges');
      case HistoryRefreshTab.EVENTS:
        return t('history_refresh_selection.search_events');
      case HistoryRefreshTab.PROTOCOLS:
        return t('history_refresh_selection.search_protocols');
    }
  });

  const typeText = computed<string>(() => {
    const total = get(totalSelected);
    switch (get(modelTab)) {
      case HistoryRefreshTab.CHAINS:
        return t('history_refresh_selection.type.accounts', total);
      case HistoryRefreshTab.EXCHANGES:
        return t('history_refresh_selection.type.exchanges', total);
      case HistoryRefreshTab.EVENTS:
        return t('history_refresh_selection.type.events', total);
      case HistoryRefreshTab.PROTOCOLS:
        return t('history_refresh_selection.type.protocols', total);
    }
  });

  function setAllSelected(tab: HistoryRefreshTab, allSelected: boolean): void {
    set(tabStates[tab].allSelected, allSelected);
  }

  function getRefreshPayload(): HistoryRefreshEventData {
    switch (get(modelTab)) {
      case HistoryRefreshTab.CHAINS:
        return { accounts: get(modelSelectedAccounts) };
      case HistoryRefreshTab.EXCHANGES:
        return { exchanges: get(modelSelectedExchanges) };
      case HistoryRefreshTab.EVENTS:
        return { queries: get(modelSelectedQueries) };
      case HistoryRefreshTab.PROTOCOLS:
        return { queries: get(modelSelectedProtocolQueries) };
    }
  }

  function reset(): void {
    set(modelSearch, '');
    set(modelSelectedChain, undefined);
    set(modelSelectedAccounts, []);
    set(allAccountsSelected, false);
    set(modelSelectedExchanges, []);
    set(allExchangesSelected, false);
    set(modelSelectedQueries, []);
    set(allQueriesSelected, false);
    set(modelSelectedProtocolQueries, []);
    set(allProtocolQueriesSelected, false);
  }

  watch(modelTab, () => {
    reset();
  });

  return {
    getRefreshPayload,
    indeterminate,
    modelSearch,
    modelSelectedAccounts,
    modelSelectedChain,
    modelSelectedExchanges,
    modelSelectedProtocolQueries,
    modelSelectedQueries,
    modelTab,
    reset,
    searchLabel,
    selected,
    setAllSelected,
    totalSelected,
    typeText,
  };
}
