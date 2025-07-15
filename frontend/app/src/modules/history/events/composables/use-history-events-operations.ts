import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventsTableEmitFn } from './types';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type {
  EvmChainAndTxHash,
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
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { isTaskCancelled } from '@/utils';

interface UseHistoryEventsOperationsOptions {
  eventsGroupedByEventIdentifier: ComputedRef<Record<string, HistoryEventRow[]>>;
  flattenedEvents: ComputedRef<HistoryEventEntry[]>;
}

interface UseHistoryEventsOperationsReturn {
  // State
  showRedecodeConfirmation: Ref<boolean>;
  redecodePayload: Ref<PullEventPayload | undefined>;

  // Functions
  getItemClass: (item: HistoryEventEntry) => '' | 'opacity-50';
  confirmDelete: (payload: HistoryEventDeletePayload) => void;
  suggestNextSequenceId: (group: HistoryEventEntry) => string;
  confirmTxAndEventsDelete: (payload: EvmChainAndTxHash) => void;
  redecode: (payload: PullEventPayload, eventIdentifier: string) => void;
  confirmRedecode: (event: { payload: PullEventPayload; deleteCustom: boolean }) => void;
  toggle: (event: HistoryEventEntry) => Promise<void>;
}

export function useHistoryEventsOperations(
  options: UseHistoryEventsOperationsOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsOperationsReturn {
  const { eventsGroupedByEventIdentifier, flattenedEvents } = options;

  const selected = ref<HistoryEventEntry[]>([]);
  const showRedecodeConfirmation = ref<boolean>(false);
  const redecodePayload = ref<PullEventPayload>();

  const { t } = useI18n();

  const { notify } = useNotificationsStore();
  const { show } = useConfirmStore();

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

  async function onConfirmTxAndEventDelete({ evmChain, txHash }: EvmChainAndTxHash): Promise<void> {
    try {
      await deleteTransactions(evmChain, txHash);
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

  function confirmTxAndEventsDelete(payload: EvmChainAndTxHash): void {
    show({
      message: t('transactions.dialog.delete.message'),
      title: t('transactions.dialog.delete.title'),
    }, async () => onConfirmTxAndEventDelete(payload));
  }

  function redecode(payload: PullEventPayload, eventIdentifier: string): void {
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', { blockNumbers: payload.data });
      return;
    }

    const groupedEvents = get(eventsGroupedByEventIdentifier)[eventIdentifier] || [];
    const childEvents = flatten(groupedEvents);
    const isAnyCustom = childEvents.some(item => item.customized);

    if (!isAnyCustom) {
      emit('refresh', { transactions: [payload.data] });
    }
    else {
      set(redecodePayload, payload);
      set(showRedecodeConfirmation, true);
    }
  }

  function confirmRedecode(event: { payload: PullEventPayload; deleteCustom: boolean }): void {
    const { deleteCustom, payload } = event;
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', {
        blockNumbers: payload.data,
      });
    }
    else {
      emit('refresh', {
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
    redecode,
    redecodePayload,
    showRedecodeConfirmation,
    suggestNextSequenceId,
    toggle,
  };
}
