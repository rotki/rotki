import type { Ref } from 'vue';
import type { HistoryRefreshEventData } from '@/modules/history/refresh/types';
import type { Collection } from '@/types/collection';
import type {
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
import { isEvmSwapEvent } from '@/modules/history/management/forms/form-guards';
import { useConfirmStore } from '@/store/confirm';
import { toEvmChainAndTxHash } from '@/utils/history';
import {
  isEthBlockEvent,
  isEvmEvent,
} from '@/utils/history/events';

interface UseHistoryEventsActionsOptions {
  onlyChains: Ref<Blockchain[]>;
  entryTypes?: Ref<HistoryEventEntryType[] | undefined>;
  currentAction: Ref<'decode' | 'query'>;
  fetchData: () => Promise<void>;
  fetchAssociatedLocations: () => Promise<void>;
  groups: Ref<Collection<HistoryEventRow>>;
  decodingStatusDialogPersistent: Ref<boolean>;
}

export function useHistoryEventsActions(options: UseHistoryEventsActionsOptions): {
  fetchAndRedecodeEvents: (data?: PullEvmTransactionPayload) => Promise<void>;
  fetchUndecodedTransactionsStatus: () => Promise<void>;
  forceRedecodeEvmEvents: (data: PullEvmTransactionPayload) => Promise<void>;
  redecode: (payload: 'all' | 'page' | string[]) => Promise<void>;
  redecodeAllEvents: () => void;
  redecodeAllEventsHandler: () => Promise<void>;
  redecodeBlockEvents: (data: PullEthBlockEventPayload) => Promise<void>;
  redecodePageTransactions: () => Promise<void>;
  redecodeTransactions: (chains: Blockchain[]) => Promise<void>;
  refresh: (userInitiated?: boolean, payload?: HistoryRefreshEventData) => Promise<void>;
  refreshTransactions: (params?: any) => Promise<void>;
} {
  const {
    currentAction,
    decodingStatusDialogPersistent,
    entryTypes,
    fetchAssociatedLocations,
    fetchData,
    groups,
    onlyChains,
  } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { show } = useConfirmStore();
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

    set(currentAction, 'query');
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
    set(currentAction, 'decode');
    await pullAndRedecodeTransactions(data);
    await fetchData();
  }

  async function fetchAndRedecodeEvents(data?: PullEvmTransactionPayload): Promise<void> {
    await fetchDataAndLocations();
    if (data)
      await forceRedecodeEvmEvents(data);
  }

  async function redecodeBlockEvents(data: PullEthBlockEventPayload): Promise<void> {
    set(currentAction, 'decode');
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
    set(decodingStatusDialogPersistent, true);
    show({
      message: t('transactions.events_decoding.confirmation'),
      title: t('transactions.events_decoding.redecode_all'),
    }, async () => redecodeAllEventsHandler(), () => {
      set(decodingStatusDialogPersistent, false);
    });
  }

  async function redecodeAllEventsHandler(): Promise<void> {
    set(decodingStatusDialogPersistent, false);
    set(currentAction, 'decode');
    await fetchUndecodedTransactionsStatus();
    await redecodeTransactions(get(onlyChains));
    await fetchData();
  }

  async function redecode(payload: 'all' | 'page' | string[]): Promise<void> {
    if (payload === 'all') {
      redecodeAllEvents();
    }
    else if (Array.isArray(payload)) {
      set(currentAction, 'decode');
      await redecodeTransactions(payload);
      await fetchData();
    }
    else if (payload === 'page') {
      await redecodePageTransactions();
    }
  }

  return {
    fetchAndRedecodeEvents,
    fetchUndecodedTransactionsStatus,
    forceRedecodeEvmEvents,
    redecode,
    redecodeAllEvents,
    redecodeAllEventsHandler,
    redecodeBlockEvents,
    redecodePageTransactions,
    redecodeTransactions,
    // Methods
    refresh,
    refreshTransactions,
  };
}
