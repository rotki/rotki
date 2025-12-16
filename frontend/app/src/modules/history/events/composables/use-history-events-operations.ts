import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventDeletePayload, HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import type {
  LocationAndTxRef,
  PullEventPayload,
} from '@/types/history/events';
import type {
  HistoryEventEntry,
  HistoryEventRow,
} from '@/types/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { flatten } from 'es-toolkit';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useIgnore } from '@/composables/history';
import { useHistoryEvents } from '@/composables/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { isTaskCancelled } from '@/utils';

interface UseHistoryEventsOperationsOptions {
  allEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  flattenedEvents: ComputedRef<HistoryEventEntry[]>;
}

interface UseHistoryEventsOperationsReturn {
  // State
  showRedecodeConfirmation: Ref<boolean>;
  redecodePayload: Ref<PullEventPayload | undefined>;
  hasCustomEvents: Ref<boolean>;
  showIndexerOptions: Ref<boolean>;

  // Functions
  getItemClass: (item: HistoryEventEntry) => '' | 'opacity-50';
  confirmDelete: (payload: HistoryEventDeletePayload) => void;
  suggestNextSequenceId: (group: HistoryEventEntry) => string;
  confirmTxAndEventsDelete: (payload: LocationAndTxRef) => void;
  redecode: (payload: PullEventPayload, eventIdentifier: string) => void;
  redecodeWithOptions: (payload: PullEventPayload, eventIdentifier: string) => void;
  confirmRedecode: (event: { payload: PullEventPayload; deleteCustom: boolean; customIndexersOrder?: string[] }) => void;
  toggle: (event: HistoryEventEntry) => Promise<void>;
}

export function useHistoryEventsOperations(
  options: UseHistoryEventsOperationsOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsOperationsReturn {
  const { allEventsMapped, flattenedEvents } = options;

  const selected = ref<HistoryEventEntry[]>([]);
  const showRedecodeConfirmation = ref<boolean>(false);
  const redecodePayload = ref<PullEventPayload>();
  const hasCustomEvents = ref<boolean>(false);
  const showIndexerOptions = ref<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });

  const { notify } = useNotificationsStore();
  const { show } = useConfirmStore();
  const { getChain } = useSupportedChains();

  const { deleteTransactions } = useHistoryEventsApi();
  const { deleteHistoryEvent } = useHistoryEvents();
  const { ignoreSingle, toggle } = useIgnore<HistoryEventEntry>({
    toData: (item: HistoryEventEntry) => item.eventIdentifier,
  }, selected, () => {
    emit('refresh');
  });

  function getItemClass(item: HistoryEventEntry): '' | 'opacity-50' {
    return item.ignoredInAccounting ? 'opacity-50' : '';
  }

  function confirmDelete(payload: HistoryEventDeletePayload): void {
    let text: { primaryAction: string; title: string; message: string };
    if (payload.type === 'ignore') {
      text = {
        message: t('transactions.events.confirmation.ignore.message'),
        primaryAction: t('transactions.events.confirmation.ignore.action'),
        title: t('transactions.events.confirmation.ignore.title'),
      };
    }
    else {
      text = {
        message: t('transactions.events.confirmation.delete.message'),
        primaryAction: t('common.actions.confirm'),
        title: t('transactions.events.confirmation.delete.title'),
      };
    }
    show(text, async () => onConfirmDelete(payload));
  }

  async function onConfirmDelete(payload: HistoryEventDeletePayload): Promise<void> {
    if (payload.type === 'ignore') {
      await ignoreSingle(payload.event, true);
    }
    else {
      const { success } = await deleteHistoryEvent(payload.ids);
      if (success)
        emit('refresh');
    }
  }

  function suggestNextSequenceId(group: HistoryEventEntry): string {
    const allFlattened = get(flattenedEvents);

    if (!allFlattened?.length)
      return (Number(group.sequenceIndex) + 1).toString();

    const eventIdentifierHeader = group.eventIdentifier;
    const filtered = allFlattened
      .filter(({ eventIdentifier, hidden }) => eventIdentifier === eventIdentifierHeader && !hidden)
      .map(({ sequenceIndex }) => Number(sequenceIndex))
      .sort((a, b) => b - a);

    return ((filtered[0] ?? Number(group.sequenceIndex)) + 1).toString();
  }

  async function onConfirmTxAndEventDelete({ location, txRef }: LocationAndTxRef): Promise<void> {
    try {
      const chain = get(getChain(location));
      await deleteTransactions(chain, txRef);
      emit('refresh');
    }
    catch (error: any) {
      if (isTaskCancelled(error))
        return;

      const title = t('transactions.dialog.delete.error.title');
      const message = t('transactions.dialog.delete.error.message', {
        message: error.message,
      });
      notify({
        display: true,
        message,
        title,
      });
    }
  }

  function confirmTxAndEventsDelete(payload: LocationAndTxRef): void {
    show({
      message: t('transactions.dialog.delete.message'),
      title: t('transactions.dialog.delete.title'),
    }, async () => onConfirmTxAndEventDelete(payload));
  }

  function isEvmPayload(payload: PullEventPayload): boolean {
    return payload.type === HistoryEventEntryType.EVM_EVENT
      || payload.type === HistoryEventEntryType.EVM_SWAP_EVENT;
  }

  function redecode(payload: PullEventPayload, eventIdentifier: string): void {
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', { blockNumbers: payload.data });
      return;
    }

    const groupedEvents = get(allEventsMapped)[eventIdentifier] || [];
    const childEvents = flatten(groupedEvents);
    const isAnyCustom = childEvents.some(item => item.customized);

    // If there are custom events, show dialog to ask about custom event handling
    if (isAnyCustom) {
      set(hasCustomEvents, true);
      set(showIndexerOptions, false);
      set(redecodePayload, payload);
      set(showRedecodeConfirmation, true);
      return;
    }

    // No custom events - just redecode directly without dialog
    emit('refresh', {
      deleteCustom: false,
      transactions: [payload.data],
    });
  }

  function redecodeWithOptions(payload: PullEventPayload, eventIdentifier: string): void {
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', { blockNumbers: payload.data });
      return;
    }

    const groupedEvents = get(allEventsMapped)[eventIdentifier] || [];
    const childEvents = flatten(groupedEvents);
    const isAnyCustom = childEvents.some(item => item.customized);

    // Show dialog with indexer options (only for EVM events)
    set(hasCustomEvents, isAnyCustom);
    set(showIndexerOptions, isEvmPayload(payload));
    set(redecodePayload, payload);
    set(showRedecodeConfirmation, true);
  }

  function confirmRedecode(event: { payload: PullEventPayload; deleteCustom: boolean; customIndexersOrder?: string[] }): void {
    const { customIndexersOrder, deleteCustom, payload } = event;
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', {
        blockNumbers: payload.data,
      });
    }
    else {
      emit('refresh', {
        customIndexersOrder,
        deleteCustom,
        transactions: [payload.data],
      });
    }
    set(redecodePayload, undefined);
  }

  return {
    confirmDelete,
    confirmRedecode,
    confirmTxAndEventsDelete,
    getItemClass,
    hasCustomEvents,
    redecode,
    redecodePayload,
    redecodeWithOptions,
    showIndexerOptions,
    showRedecodeConfirmation,
    suggestNextSequenceId,
    toggle,
  };
}
