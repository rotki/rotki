import type { MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { DialogEventHandlers } from '@/modules/history/events/dialog-types';
import type {
  DecodeScope,
  LocationAndTxRef,
  PullEthBlockEventPayload,
  PullLocationTransactionPayload,
} from '@/modules/history/events/event-payloads';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import { type Blockchain, HistoryEventEntryType } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import {
  isEthBlockEvent,
  isEvmEvent,
  isEvmSwapEvent,
  isSolanaEvent,
  toLocationAndTxRef,
} from '@/modules/history/event-utils';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import { useTargetedRedecode } from '@/modules/history/events/tx/use-targeted-redecode';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { useHistoryEventsAutoFetch } from '@/modules/history/events/use-history-events-auto-fetch';
import { useHistoryEventsDialogHandlers } from '@/modules/history/events/use-history-events-dialog-handlers';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useHistoryStore } from '@/modules/history/use-history-store';

interface UseHistoryEventsActionsOptions {
  /** Blockchain chains to restrict event queries to. */
  onlyChains: MaybeRefOrGetter<Blockchain[]>;
  /** Entry types to filter on; when set, EVM events may be skipped during refresh. */
  entryTypes?: MaybeRefOrGetter<HistoryEventEntryType[] | undefined>;
  /** Callback to fetch the current page of history events. */
  refetch: () => Promise<void>;
  /** The current collection of grouped history event rows. */
  groups: Ref<Collection<HistoryEventRow>>;
  /** Marks this as the main history page; only then does an external event modification (e.g. from the pinned sidebar) trigger a refetch. */
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
    by: (scope: DecodeScope) => Promise<void>;
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
    entryTypes,
    refetch: fetchEventsData,
    groups,
    mainPage,
    onlyChains,
    shouldFetchEventsRegularly,
    showDialog,
  } = options;

  const { t } = useI18n({ useScope: 'global' });
  const route = useRoute();
  const { fetchCustomizedEventDuplicates } = useCustomizedEventDuplicates();

  async function readTable(): Promise<void> {
    await fetchEventsData();
    if (get(route).query.groupIdentifiers)
      await fetchCustomizedEventDuplicates();
  }

  /**
   * Reads the events table, one read at a time, and folds callers that arrive together into one.
   *
   * @remarks
   * `useTableData.refetch` opens with `api.cancelByTag`, so overlapping reads cancel each other
   * onto one shared `useAsyncState` and the table can end up holding the loser's result — which,
   * if empty, empties the table. So reads never overlap.
   *
   * A caller arriving while a read runs gets a follow-up read, since the running one may predate
   * what it wants to see. Callers arriving while that follow-up waits join it: it starts after they
   * called, so it shows what each of them wants. At most one read runs and one waits, however many
   * watchers fire at the end of a run. A rejected read does not block the next.
   */
  let running: Promise<void> | undefined;
  let waiting: Promise<void> | undefined;

  async function startRead(): Promise<void> {
    const read = readTable().finally(() => {
      if (running === read)
        running = undefined;
    });
    running = read;
    return read;
  }

  async function fetchData(): Promise<void> {
    if (waiting)
      return waiting;

    if (!running)
      return startRead();

    const next = running.catch(() => {}).then(async () => {
      waiting = undefined;
      return startRead();
    });
    waiting = next;
    return next;
  }

  const { show } = useConfirmStore();
  const { fetchAssociatedLocations, fetchLocationLabels } = useHistoryDataFetching();
  const historyStore = useHistoryStore();
  const { eventsVersion } = storeToRefs(historyStore);
  const { refreshTransactions } = useHistoryTransactions();
  const { checkMissingEventsAndRedecode, fetchUndecodedTransactionsBreakdown, redecodeTransactions } = useHistoryTransactionDecoding();
  const { redecodeTargeted } = useTargetedRedecode();
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

    const entryTypesVal = toValue(entryTypes) ?? [];
    const disableEvmEvents = entryTypesVal.length > 0 && !entryTypesVal.includes(HistoryEventEntryType.EVM_EVENT);
    await refreshTransactions({
      chains: toValue(onlyChains),
      disableEvmEvents,
      payload,
      userInitiated,
    });
  }

  async function forceRedecodeEvmEvents(data: PullLocationTransactionPayload): Promise<void> {
    await redecodeTargeted(data);
    await fetchDataAndLocations();
  }

  /**
   * Re-decodes events and reloads the table.
   *
   * @remarks
   * With a payload, only the redecode's own trailing fetch runs: `forceRedecodeEvmEvents` fetches
   * when it finishes, so fetching first as well reads the table twice for one action and the first
   * read shows pre-redecode data that is immediately replaced.
   */
  async function fetchAndRedecodeEvents(data?: PullLocationTransactionPayload): Promise<void> {
    if (data) {
      await forceRedecodeEvmEvents(data);
      return;
    }

    await fetchDataAndLocations();
  }

  async function redecodeBlockEvents(data: PullEthBlockEventPayload): Promise<void> {
    await redecodeTargeted(data);
    await fetchDataAndLocations();
  }

  /**
   * Development-only: re-decodes whatever the current page shows.
   *
   * @remarks
   * Transactions and block events go to the targeted re-decode as one request, so a page holding
   * both kinds produces a single set of activities naming the one thing the user asked for.
   */
  async function redecodePageTransactions(): Promise<void> {
    const events = get(groups).data.flat();
    const txEvents = events.filter(event => isEvmEvent(event) || isEvmSwapEvent(event) || isSolanaEvent(event));
    const ethBlockEvents = events.filter(isEthBlockEvent);

    if (txEvents.length > 0 || ethBlockEvents.length > 0) {
      const transactions: LocationAndTxRef[] = txEvents.map(toLocationAndTxRef);
      await redecodeTargeted({
        blockNumbers: ethBlockEvents.map(item => item.blockNumber),
        transactions,
      });

      if (txEvents.length > 0)
        await fetchUndecodedTransactionsBreakdown();

      await fetchDataAndLocations();
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
    await fetchUndecodedTransactionsBreakdown();
    await redecodeTransactions(toValue(onlyChains));
    await fetchDataAndLocations();
  }

  async function redecode(scope: DecodeScope): Promise<void> {
    switch (scope.type) {
      case 'all':
        redecodeAllEvents();
        break;
      case 'chains':
        await redecodeTransactions(scope.chains);
        await fetchDataAndLocations();
        break;
      case 'page':
        await redecodePageTransactions();
        break;
    }
  }

  // Set up auto-fetch functionality if shouldFetchEventsRegularly is provided
  const autoFetch = shouldFetchEventsRegularly
    ? useHistoryEventsAutoFetch(shouldFetchEventsRegularly, {
        onProgress: fetchData,
        onSettle: fetchDataAndLocations,
      })
    : undefined;

  if (mainPage) {
    watch(eventsVersion, (current, previous) => {
      if (!toValue(mainPage) || current <= previous)
        return;

      if (autoFetch)
        autoFetch.markStale();
      else
        startPromise(fetchData());
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
      undecodedStatus: fetchUndecodedTransactionsBreakdown,
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
