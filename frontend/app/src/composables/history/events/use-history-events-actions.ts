import type { Ref } from 'vue';
import type { DialogEventHandlers } from '@/components/history/events/dialog-types';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import type { Collection } from '@/types/collection';
import type {
  EvmChainAndTxHash,
  PullEthBlockEventPayload,
  PullEvmTransactionPayload,
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
import { toEvmChainAndTxHash } from '@/utils/history';
import {
  isEthBlockEvent,
  isEvmEvent,
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
    dataAndRedecode: (data?: PullEvmTransactionPayload) => Promise<void>;
    undecodedStatus: () => Promise<void>;
  };
  redecode: {
    all: () => void; // Shows confirmation dialog
    blocks: (data: PullEthBlockEventPayload) => Promise<void>;
    by: (payload: 'all' | 'page' | string[]) => Promise<void>; // Current unified redecode
    evm: (data: PullEvmTransactionPayload) => Promise<void>;
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
  const { fetchAssociatedLocations, resetUndecodedTransactionsStatus } = useHistoryStore();
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
    await fetchAssociatedLocations();
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
    startPromise(fetchDataAndLocations());
  }

  async function forceRedecodeEvmEvents(data: PullEvmTransactionPayload): Promise<void> {
    set(currentAction, HISTORY_EVENT_ACTIONS.DECODE);
    await pullAndRedecodeTransactions(data);
    await fetchData();
  }

  async function fetchAndRedecodeEvents(data?: PullEvmTransactionPayload): Promise<void> {
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
    const evmEvents = events.filter(event => isEvmEvent(event) || isEvmSwapEvent(event));
    const ethBlockEvents = events.filter(isEthBlockEvent);

    if (evmEvents.length > 0 || ethBlockEvents.length > 0) {
      if (evmEvents.length > 0) {
        const redecodePayload = evmEvents.map(item => toEvmChainAndTxHash(item));
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
  const handleTransactionRecode = async (txHash: EvmChainAndTxHash): Promise<void> => {
    await forceRedecodeEvmEvents({ transactions: [txHash] });
  };

  const dialogHandlers: DialogEventHandlers = {
    onHistoryEventSaved: fetchDataAndLocations,
    onRedecodeAllEvents: redecodeAllEvents,
    onRedecodeTransaction: handleTransactionRecode,
    onRepullTransactions: async (chains: string[]): Promise<void> => {
      await refreshTransactions({
        chains,
        disableEvmEvents: false,
        payload: undefined,
        userInitiated: true,
      });
    },
    onResetUndecodedTransactions: (): void => {
      resetUndecodedTransactionsStatus();
    },
    onTransactionAdded: handleTransactionRecode,
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
