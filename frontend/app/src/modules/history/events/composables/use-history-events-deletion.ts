import type { Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { Collection } from '@/types/collection';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { HistoryEventEntryType, Severity } from '@rotki/common';
import { get } from '@vueuse/shared';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useIgnore } from '@/composables/history';
import { useHistoryEvents } from '@/composables/history/events';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';

interface TransactionGroup {
  chain: string;
  eventIdentifier: string;
  events: number[];
}

interface DeletionStrategy {
  eventIds?: number[];
  transactions?: Map<string, TransactionGroup>;
  type: 'delete-transactions' | 'ignore-events' | 'delete-events';
}

interface UseHistoryEventsDeletionReturn {
  deleteSelected: () => Promise<void>;
  isDeleting: Readonly<Ref<boolean>>;
}

export function useHistoryEventsDeletion(
  selectionMode: UseHistoryEventsSelectionModeReturn,
  groupedEventsByTxHash: Ref<Record<string, HistoryEventRow[]>>,
  groups: Ref<Collection<HistoryEventRow>>,
  refreshCallback: () => Promise<void>,
): UseHistoryEventsDeletionReturn {
  const { t } = useI18n();
  const { show: showConfirm } = useConfirmStore();
  const { notify } = useNotificationsStore();
  const { deleteTransactions } = useHistoryEventsApi();
  const { deleteHistoryEvent } = useHistoryEvents();

  const { ignoreSingle } = useIgnore<HistoryEventEntry>(
    { toData: item => item.eventIdentifier },
    ref([]),
    refreshCallback,
  );

  const isDeleting = ref<boolean>(false);

  function analyzeSelectedEvents(selectedIds: number[]): {
    completeTransactions: Map<string, TransactionGroup>;
    partialEventIds: number[];
  } {
    const selectedSet = new Set(selectedIds);
    const completeTransactions = new Map<string, TransactionGroup>();
    const groupedEvents = get(groupedEventsByTxHash);
    const allGroups = get(groups).data;

    // Check each EVM transaction
    allGroups.forEach((group) => {
      if (!Array.isArray(group) && group.entryType === HistoryEventEntryType.EVM_EVENT) {
        const eventIdentifier = group.eventIdentifier;
        const txEvents = groupedEvents[eventIdentifier];

        if (txEvents && txEvents.length > 0) {
          // Get all event IDs for this transaction
          const eventIds = txEvents.flatMap((event: HistoryEventRow) =>
            Array.isArray(event) ? event.map(e => e.identifier) : event.identifier,
          );

          // Check if all events are selected
          const allSelected = eventIds.length > 0 && eventIds.every((id: number) => selectedSet.has(id));

          if (allSelected) {
            // Use the actual txRef from the group if it's an EVM event
            const txRef = 'txRef' in group && group.txRef ? group.txRef : group.eventIdentifier;
            completeTransactions.set(txRef, {
              chain: group.location,
              eventIdentifier, // Store the eventIdentifier for lookup
              events: eventIds,
            });
          }
        }
      }
    });

    // Get remaining event IDs after excluding complete transaction events
    const completeEventIds = new Set(
      Array.from(completeTransactions.values()).flatMap(({ events }) => events),
    );
    const partialEventIds = selectedIds.filter(id => !completeEventIds.has(id));

    return { completeTransactions, partialEventIds };
  }

  function buildDeletionConfirmationMessage(
    strategy: DeletionStrategy,
  ): {
    message: string;
    primaryAction: string;
    secondaryAction?: string;
    title: string;
  } {
    switch (strategy.type) {
      case 'delete-transactions': {
        const count = strategy.transactions?.size ?? 0;
        const message = count === 1
          ? t('transactions.events.confirmation.delete.complete_transaction_single')
          : t('transactions.events.confirmation.delete.complete_transaction_multiple', { count });
        return {
          message: `${message}\n\n${t('transactions.events.confirmation.delete.complete_transaction_options')}`,
          primaryAction: t('transactions.events.confirmation.delete.delete_transaction'),
          secondaryAction: t('transactions.events.confirmation.ignore.action_short'),
          title: t('transactions.events.confirmation.delete.complete_transaction_title'),
        };
      }

      case 'delete-events':
        return {
          message: t('transactions.events.confirmation.delete.message_multiple', {
            count: strategy.eventIds?.length ?? 0,
          }),
          primaryAction: t('common.actions.confirm'),
          title: t('transactions.events.confirmation.delete.title'),
        };

      case 'ignore-events': {
        const count = strategy.transactions?.size ?? 0;
        return {
          message: t('transactions.events.confirmation.ignore.message_multiple', { count }),
          primaryAction: t('transactions.events.confirmation.ignore.confirm'),
          title: t('transactions.events.confirmation.ignore.title'),
        };
      }

      default:
        throw new Error('Unknown deletion strategy');
    }
  }

  async function deleteCompleteTransactions(
    transactions: Map<string, TransactionGroup>,
  ): Promise<{ message?: string; success: boolean }> {
    try {
      for (const [txHash, { chain }] of transactions)
        await deleteTransactions(chain, txHash);

      return { success: true };
    }
    catch (error: any) {
      return {
        message: error.message,
        success: false,
      };
    }
  }

  async function deletePartialEvents(
    eventIds: number[],
  ): Promise<{ message?: string; success: boolean }> {
    if (eventIds.length === 0)
      return { success: true };

    return deleteHistoryEvent(eventIds, false);
  }

  async function ignoreTransactionEvents(
    transactions: Map<string, TransactionGroup>,
  ): Promise<{ message?: string; success: boolean }> {
    try {
      for (const [, { eventIdentifier, events: eventIds }] of transactions) {
        // Use eventIdentifier to look up the events (groupedEventsByTxHash is keyed by eventIdentifier)
        const txEvents = eventIdentifier ? get(groupedEventsByTxHash)[eventIdentifier] || [] : [];

        // Flatten the events array
        const allEvents = txEvents.flat().filter((e: any) => !Array.isArray(e));

        // Ignore each event that matches our selected IDs
        for (const eventId of eventIds) {
          const event = allEvents.find((e: HistoryEventEntry) => e.identifier === eventId);
          if (event)
            await ignoreSingle(event, true);
        }
      }
      return { success: true };
    }
    catch (error: any) {
      return {
        message: error.message,
        success: false,
      };
    }
  }

  function notifyCaller(
    title: string,
    message: string,
    success = false,
  ): void {
    notify({
      display: true,
      message,
      severity: success ? Severity.INFO : Severity.ERROR,
      title,
    });
  }

  function notifyDeletionResult(
    success: boolean,
    count: number,
    type: 'delete' | 'ignore',
    message?: string,
  ): void {
    if (type === 'delete') {
      if (success) {
        notifyCaller(
          t('transactions.events.delete.title'),
          t('transactions.events.delete.success', { count }),
          true,
        );
      }
      else {
        notifyCaller(
          t('transactions.events.delete.error.title'),
          message || t('transactions.events.delete.error.message'),
        );
      }
    }
    else if (type === 'ignore') {
      if (success) {
        notifyCaller(
          t('transactions.events.ignore.title'),
          t('transactions.events.ignore.success', { count }),
          true,
        );
      }
      else {
        notifyCaller(
          t('transactions.events.ignore.error.title'),
          message || t('transactions.events.ignore.error.message'),
        );
      }
    }
  }

  async function deleteSelected(): Promise<void> {
    const selectedIds = selectionMode.getSelectedIds();
    if (selectedIds.length === 0)
      return;

    set(isDeleting, true);

    try {
      const { completeTransactions, partialEventIds } = analyzeSelectedEvents(selectedIds);

      if (completeTransactions.size > 0)
        await handleCompleteTransactionDeletion(completeTransactions, partialEventIds, selectedIds.length);
      else
        await handlePartialEventDeletion(partialEventIds);
    }
    finally {
      set(isDeleting, false);
    }
  }

  async function handleCompleteTransactionDeletion(
    transactions: Map<string, TransactionGroup>,
    remainingEventIds: number[],
    totalCount: number,
  ): Promise<void> {
    const strategy: DeletionStrategy = {
      eventIds: remainingEventIds,
      transactions,
      type: 'delete-transactions',
    };

    const confirmation = buildDeletionConfirmationMessage(strategy);

    await new Promise<void>((resolve) => {
      showConfirm(
        confirmation,
        // Primary: Delete transactions
        async () => {
          const txResult = await deleteCompleteTransactions(transactions);
          const eventsResult = await deletePartialEvents(remainingEventIds);

          const success = txResult.success && eventsResult.success;
          const message = txResult.message || eventsResult.message;
          notifyDeletionResult(success, totalCount, 'delete', message);

          if (success) {
            selectionMode.actions.exit();
            await refreshCallback();
          }
          resolve();
        },
        // Secondary: Ignore in accounting
        async () => {
          await handleIgnoreOption(transactions, remainingEventIds);
          resolve();
        },
      );
    });
  }

  async function handlePartialEventDeletion(
    eventIds: number[],
  ): Promise<void> {
    const strategy: DeletionStrategy = {
      eventIds,
      type: 'delete-events',
    };

    const confirmation = buildDeletionConfirmationMessage(strategy);

    await new Promise<void>((resolve) => {
      showConfirm(
        confirmation,
        async () => {
          const result = await deletePartialEvents(eventIds);
          notifyDeletionResult(result.success, eventIds.length, 'delete', result.message);

          if (result.success) {
            selectionMode.actions.exit();
            await refreshCallback();
          }
          resolve();
        },
      );
    });
  }

  async function handleIgnoreOption(
    transactions: Map<string, TransactionGroup>,
    remainingEventIds: number[],
  ): Promise<void> {
    const ignoreStrategy: DeletionStrategy = {
      transactions,
      type: 'ignore-events',
    };

    const ignoreConfirmation = buildDeletionConfirmationMessage(ignoreStrategy);

    await new Promise<void>((resolve) => {
      showConfirm(
        ignoreConfirmation,
        async () => {
          const ignoreResult = await ignoreTransactionEvents(transactions);
          const deleteResult = await deletePartialEvents(remainingEventIds);

          const success = ignoreResult.success && deleteResult.success;
          const message = ignoreResult.message || deleteResult.message;
          notifyDeletionResult(success, transactions.size, 'ignore', message);

          if (success) {
            selectionMode.actions.exit();
            await refreshCallback();
          }
          resolve();
        },
      );
    });
  }

  return {
    deleteSelected,
    isDeleting: readonly(isDeleting),
  };
}
