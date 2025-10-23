import type { Ref } from 'vue';
import type { DialogEventHandlers } from '@/components/history/events/dialog-types';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import type { Collection } from '@/types/collection';
import type { Exchange } from '@/types/exchanges';
import type {
  ChainAddress,
  LocationAndTxHash,
  PullEthBlockEventPayload,
  PullLocationTransactionPayload,
} from '@/types/history/events';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { type Blockchain, HistoryEventEntryType } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { flatten } from 'es-toolkit';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { HISTORY_EVENT_ACTIONS, type HistoryEventAction } from '@/composables/history/events/types';
import { useHistoryEventsAutoFetch } from '@/modules/history/events/use-history-events-auto-fetch';
import { isEvmSwapEvent } from '@/modules/history/management/forms/form-guards';
import { useConfirmStore } from '@/store/confirm';
import { useHistoryStore } from '@/store/history';
import { toLocationAndTxHash } from '@/utils/history';
import {
  isEthBlockEvent,
  isEvmEvent,
  isSolanaEvent,
} from '@/utils/history/events';

interface UseHistoryEventsActionsOptions {
  onlyChains: Ref<Blockchain[]>;
  entryTypes?: Ref<HistoryEventEntryType[] | undefined>;
  currentAction: Ref<HistoryEventAction>;
  fetchData: () => Promise<void>;
  groups: Ref<Collection<HistoryEventRow>>;
  shouldFetchEventsRegularly?: Ref<boolean>;
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
    fetchData,
    groups,
    onlyChains,
    shouldFetchEventsRegularly,
    showDialog,
  } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { show } = useConfirmStore();
  const {
    fetchAssociatedLocations,
    fetchLocationLabels,
    resetUndecodedTransactionsStatus,
  } = useHistoryStore();
  const { refreshTransactions } = useHistoryTransactions();
  const {
    fetchUndecodedTransactionsStatus,
    pullAndRecodeEthBlockEvents,
    pullAndRedecodeTransactions,
    redecodeTransactions,
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
    const entryTypesVal = get(entryTypes) || [];
    const disableEvmEvents = entryTypesVal.length > 0 && !entryTypesVal.includes(HistoryEventEntryType.EVM_EVENT);
    await refreshTransactions({
      chains: get(onlyChains),
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
    const events = flatten(get(groups).data);
    const txEvents = events.filter(event => isEvmEvent(event) || isEvmSwapEvent(event) || isSolanaEvent(event));
    const ethBlockEvents = events.filter(isEthBlockEvent);

    if (txEvents.length > 0 || ethBlockEvents.length > 0) {
      if (txEvents.length > 0) {
        const redecodePayload: LocationAndTxHash[] = txEvents.map(toLocationAndTxHash);
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
    await redecodeTransactions(get(onlyChains));
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

  // Dialog handlers
  const handleTransactionRedecode = async (txHash: LocationAndTxHash): Promise<void> => {
    await forceRedecodeEvmEvents({ transactions: [txHash] });
  };

  const dialogHandlers: DialogEventHandlers = {
    onHistoryEventSaved: fetchDataAndLocations,
    onRedecodeAllEvents: redecodeAllEvents,
    onRedecodeTransaction: handleTransactionRedecode,
    onRepullExchangeEvents: async (exchanges: Exchange[]): Promise<void> => {
      await refreshTransactions({
        disableEvmEvents: true,
        payload: {
          exchanges,
        },
        userInitiated: true,
      });
    },
    onRepullTransactions: async (account: ChainAddress): Promise<void> => {
      if (account.address) {
        await refreshTransactions({
          chains: [],
          disableEvmEvents: false,
          payload: {
            accounts: [account],
          },
          userInitiated: true,
        });
      }
      else {
        await refreshTransactions({
          chains: [account.chain],
          disableEvmEvents: false,
          payload: undefined,
          userInitiated: true,
        });
      }
    },
    onResetUndecodedTransactions: (): void => {
      resetUndecodedTransactionsStatus();
    },
    onTransactionAdded: handleTransactionRedecode,
  };

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
