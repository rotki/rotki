import type { Ref } from 'vue';
import type { DialogEventHandlers } from '@/components/history/events/dialog-types';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import type { Collection } from '@/types/collection';
import type { Exchange } from '@/types/exchanges';
import type {
  LocationAndTxRef,
  PullEthBlockEventPayload,
  PullLocationTransactionPayload,
} from '@/types/history/events';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { type Blockchain, HistoryEventEntryType, type NotificationAction, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { type RepullingTransactionResult, useHistoryTransactions } from '@/composables/history/events/tx';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { HISTORY_EVENT_ACTIONS, type HistoryEventAction } from '@/composables/history/events/types';
import { useHistoryEventsAutoFetch } from '@/modules/history/events/use-history-events-auto-fetch';
import { Routes } from '@/router/routes';
import { useConfirmStore } from '@/store/confirm';
import { useHistoryStore } from '@/store/history';
import { useNotificationsStore } from '@/store/notifications';
import { toLocationAndTxRef } from '@/utils/history';
import {
  isEthBlockEvent,
  isEvmEvent,
  isEvmSwapEvent,
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
  const router = useRouter();
  const { show } = useConfirmStore();
  const { notify } = useNotificationsStore();
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
  const handleTransactionRedecode = async (txRef: LocationAndTxRef): Promise<void> => {
    await forceRedecodeEvmEvents({ transactions: [txRef] });
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
    onRepullTransactions: async (result: RepullingTransactionResult): Promise<void> => {
      await checkMissingEventsAndRedecode();

      const { newTransactions, newTransactionsCount } = result;

      let action: NotificationAction | undefined;
      if (newTransactionsCount > 0) {
        const allTxHashes = Object.values(newTransactions).flat();
        action = {
          action: async (): Promise<void> => {
            await router.push({
              path: Routes.HISTORY_EVENTS.toString(),
              query: { txRefs: allTxHashes },
            });
          },
          label: t('actions.repulling_transaction.success.action'),
        };
      }

      notify({
        action,
        display: true,
        message: newTransactionsCount ? t('actions.repulling_transaction.success.description', { length: newTransactionsCount }) : t('actions.repulling_transaction.success.no_tx_description'),
        severity: Severity.INFO,
        title: t('actions.repulling_transaction.task.title'),
      });
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
