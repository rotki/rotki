import type { MaybeRefOrGetter, Ref } from 'vue';
import type { DialogEventHandlers } from '@/components/history/events/dialog-types';
import type { Collection } from '@/modules/common/collection';
import type {
  LocationAndTxRef,
  PullEthBlockEventPayload,
  PullLocationTransactionPayload,
} from '@/modules/history/events/event-payloads';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import { type Blockchain, HistoryEventEntryType } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { HISTORY_EVENT_ACTIONS, type HistoryEventAction } from '@/composables/history/events/types';
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { useHistoryEventsDialogHandlers } from '@/composables/history/events/use-history-events-dialog-handlers';
import {
  isEthBlockEvent,
  isEvmEvent,
  isEvmSwapEvent,
  isSolanaEvent,
  toLocationAndTxRef,
} from '@/modules/history/event-utils';
import { useHistoryEventsAutoFetch } from '@/modules/history/events/use-history-events-auto-fetch';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useConfirmStore } from '@/store/confirm';
import { useHistoryStore } from '@/store/history';

interface UseHistoryEventsActionsOptions {
  /** Blockchain chains to restrict event queries to. */
  onlyChains: MaybeRefOrGetter<Blockchain[]>;
  /** Entry types to filter on; when set, EVM events may be skipped during refresh. */
  entryTypes?: MaybeRefOrGetter<HistoryEventEntryType[] | undefined>;
  /** Tracks the current action state (e.g. querying, decoding). */
  currentAction: Ref<HistoryEventAction>;
  /** Callback to fetch the current page of history events. */
  fetchData: () => Promise<void>;
  /** The current collection of grouped history event rows. */
  groups: Ref<Collection<HistoryEventRow>>;
  mainPage?: MaybeRefOrGetter<boolean>;
  /** When provided, enables periodic auto-fetching of events. */
  shouldFetchEventsRegularly?: Ref<boolean>;
  /** Opens a dialog (e.g. decoding status) when redecoding all events. */
  showDialog?: (options: { type: 'decodingStatus'; persistent?: boolean }) => Promise<void>;
}

interface UseHistoryEventsActionsReturn {
  dialogHandlers: DialogEventHandlers;
  fetch: {
    dataAndLocations: () => Promise<void>;
    dataAndRedecode: (data?: PullLocationTransactionPayload) => Promise<void>;
    undecodedStatus: () => Promise<void>;
  };
  redecode: {
    all: () => void; // Shows confirmation dialog
    blocks: (data: PullEthBlockEventPayload) => Promise<void>;
    by: (payload: 'all' | 'page' | string[]) => Promise<void>; // Current unified redecode
    evm: (data: PullLocationTransactionPayload) => Promise<void>;
    page: () => Promise<void>;
    transactions: (chains: Blockchain[]) => Promise<void>;
  };
  refresh: {
    all: (userInitiated?: boolean, payload?: HistoryRefreshEventData) => Promise<void>;
    transactions: (params?: any) => Promise<void>;
  };
}

export function useHistoryEventsActions(options: UseHistoryEventsActionsOptions): UseHistoryEventsActionsReturn {
  const {
    currentAction,
    entryTypes,
    fetchData: fetchEventsData,
    groups,
    mainPage,
    onlyChains,
    shouldFetchEventsRegularly,
    showDialog,
  } = options;

  const { t } = useI18n({ useScope: 'global' });
  const route = useRoute();
  const { fetchCustomizedEventDuplicates } = useCustomizedEventDuplicates();

  async function fetchData(): Promise<void> {
    await fetchEventsData();
    if (get(route).query.groupIdentifiers)
      await fetchCustomizedEventDuplicates();
  }

  const { show } = useConfirmStore();
  const { fetchAssociatedLocations, fetchLocationLabels } = useHistoryDataFetching();
  const historyStore = useHistoryStore();
  const { eventsVersion } = storeToRefs(historyStore);
  const { refreshTransactions } = useHistoryTransactions();
  const {
    fetchUndecodedTransactionsStatus,
    pullAndRecodeEthBlockEvents,
    pullAndRedecodeTransactions,
    redecodeTransactions,
    checkMissingEventsAndRedecode,
  } = useHistoryTransactionDecoding();
  const historyEventMappings = useHistoryEventMappings();

  async function fetchDataAndLocations(): Promise<void> {
    await fetchData();
    await Promise.all([
      fetchAssociatedLocations(),
      fetchLocationLabels(),
    ]);
  }

  async function refresh(userInitiated = false, payload?: HistoryRefreshEventData): Promise<void> {
    if (userInitiated)
      startPromise(historyEventMappings.refresh());
    else
      startPromise(fetchDataAndLocations());

    set(currentAction, HISTORY_EVENT_ACTIONS.QUERY);
    const entryTypesVal = toValue(entryTypes) || [];
    const disableEvmEvents = entryTypesVal.length > 0 && !entryTypesVal.includes(HistoryEventEntryType.EVM_EVENT);
    await refreshTransactions({
      chains: toValue(onlyChains),
      disableEvmEvents,
      payload,
      userInitiated,
    });
  }

  async function forceRedecodeEvmEvents(data: PullLocationTransactionPayload): Promise<void> {
    set(currentAction, HISTORY_EVENT_ACTIONS.DECODE);
    await pullAndRedecodeTransactions(data);
    await fetchData();
  }

  async function fetchAndRedecodeEvents(data?: PullLocationTransactionPayload): Promise<void> {
    await fetchDataAndLocations();
    if (data)
      await forceRedecodeEvmEvents(data);
  }

  async function redecodeBlockEvents(data: PullEthBlockEventPayload): Promise<void> {
    set(currentAction, HISTORY_EVENT_ACTIONS.DECODE);
    await pullAndRecodeEthBlockEvents(data);
    await fetchData();
  }

  async function redecodePageTransactions(): Promise<void> {
    const events = get(groups).data.flat();
    const txEvents = events.filter(event => isEvmEvent(event) || isEvmSwapEvent(event) || isSolanaEvent(event));
    const ethBlockEvents = events.filter(isEthBlockEvent);

    if (txEvents.length > 0 || ethBlockEvents.length > 0) {
      if (txEvents.length > 0) {
        const redecodePayload: LocationAndTxRef[] = txEvents.map(toLocationAndTxRef);
        await pullAndRedecodeTransactions({ transactions: redecodePayload });
        await fetchUndecodedTransactionsStatus();
      }

      if (ethBlockEvents.length > 0) {
        const redecodePayload = ethBlockEvents.map(item => item.blockNumber);
        await redecodeBlockEvents({ blockNumbers: redecodePayload });
      }

      await fetchData();
    }
  }

  function redecodeAllEvents(): void {
    if (showDialog)
      startPromise(showDialog({ persistent: true, type: 'decodingStatus' }));

    show({
      message: t('transactions.events_decoding.confirmation'),
      title: t('transactions.events_decoding.redecode_all'),
    }, redecodeAllEventsHandler);
  }

  async function redecodeAllEventsHandler(): Promise<void> {
    set(currentAction, HISTORY_EVENT_ACTIONS.DECODE);
    await fetchUndecodedTransactionsStatus();
    await redecodeTransactions(toValue(onlyChains));
    await fetchData();
  }

  async function redecode(payload: 'all' | 'page' | string[]): Promise<void> {
    if (payload === 'all') {
      redecodeAllEvents();
    }
    else if (Array.isArray(payload)) {
      set(currentAction, HISTORY_EVENT_ACTIONS.DECODE);
      await redecodeTransactions(payload);
      await fetchData();
    }
    else if (payload === 'page') {
      await redecodePageTransactions();
    }
  }

  // Set up auto-fetch functionality if shouldFetchEventsRegularly is provided
  if (shouldFetchEventsRegularly) {
    useHistoryEventsAutoFetch(shouldFetchEventsRegularly, fetchDataAndLocations);
  }

  // Refresh when events are modified (e.g., from pinned sidebar matching)
  if (mainPage) {
    watch(eventsVersion, async (current, previous) => {
      if (toValue(mainPage) && current > previous)
        await fetchDataAndLocations();
    });
  }

  const dialogHandlers = useHistoryEventsDialogHandlers({
    checkMissingEventsAndRedecode,
    fetchDataAndLocations,
    forceRedecodeEvmEvents,
    redecodeAllEvents,
    refreshTransactions,
  });

  return {
    dialogHandlers,
    fetch: {
      dataAndLocations: fetchDataAndLocations,
      dataAndRedecode: fetchAndRedecodeEvents,
      undecodedStatus: fetchUndecodedTransactionsStatus,
    },
    redecode: {
      all: redecodeAllEvents,
      blocks: redecodeBlockEvents,
      by: redecode,
      evm: forceRedecodeEvmEvents,
      page: redecodePageTransactions,
      transactions: redecodeTransactions,
    },
    refresh: {
      all: refresh,
      transactions: refreshTransactions,
    },
  };
}
