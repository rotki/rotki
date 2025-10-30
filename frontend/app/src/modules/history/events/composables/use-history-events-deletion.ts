import type { Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { Severity } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useIgnore } from '@/composables/history';
import { useHistoryEvents } from '@/composables/history/events';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { buildDeletionConfirmationMessage, DELETION_STRATEGY_TYPE, type DeletionStrategy } from './use-deletion-strategies';
import { analyzeSelectedEvents, type TransactionGroup } from './use-event-analysis';

interface UseHistoryEventsDeletionReturn {
  deleteSelected: () => Promise<void>;
  isDeleting: Readonly<Ref<boolean>>;
}

export function useHistoryEventsDeletion(
  selectionMode: UseHistoryEventsSelectionModeReturn,
  groupedEventsByTxRef: Ref<Record<string, HistoryEventRow[]>>,
  originalGroups: Ref<HistoryEventRow[]>,
  refreshCallback: () => Promise<void>,
): UseHistoryEventsDeletionReturn {
  const { t } = useI18n({ useScope: 'global' });
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

  async function deleteCompleteTransactions(
    transactions: Map<string, TransactionGroup>,
  ): Promise<{ message?: string; success: boolean }> {
    try {
      for (const [txRef, { chain }] of transactions)
        await deleteTransactions(chain, txRef);

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
        // Use eventIdentifier to look up the events
        const txEvents = eventIdentifier ? get(groupedEventsByTxRef)[eventIdentifier] || [] : [];

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

  function notifyDeletionResult(
    success: boolean,
    count: number,
    type: 'delete' | 'ignore',
    message?: string,
  ): void {
    const title = type === 'delete'
      ? t('transactions.events.delete.title')
      : t('transactions.events.ignore.title');

    const successMessage = type === 'delete'
      ? t('transactions.events.delete.success', { count })
      : t('transactions.events.ignore.success', { count });

    const errorTitle = type === 'delete'
      ? t('transactions.events.delete.error.title')
      : t('transactions.events.ignore.error.title');

    const errorMessage = type === 'delete'
      ? message || t('transactions.events.delete.error.message')
      : message || t('transactions.events.ignore.error.message');

    notify({
      display: true,
      message: success ? successMessage : errorMessage,
      severity: success ? Severity.INFO : Severity.ERROR,
      title: success ? title : errorTitle,
    });
  }

  async function deleteSelected(): Promise<void> {
    const selectedIds = selectionMode.getSelectedIds();
    if (selectedIds.length === 0)
      return;

    set(isDeleting, true);

    try {
      const { completeTransactions, partialEventIds, partialSwapGroups } = analyzeSelectedEvents(
        selectedIds,
        get(originalGroups),
        get(groupedEventsByTxRef),
      );

      // Handle partial swap selection first
      if (partialSwapGroups.length > 0) {
        await handlePartialSwapDeletion(partialSwapGroups, partialEventIds, completeTransactions);
      }
      else if (completeTransactions.size > 0) {
        await handleCompleteTransactionDeletion(completeTransactions, partialEventIds, selectedIds.length);
      }
      else {
        await handlePartialEventDeletion(partialEventIds, selectedIds.length);
      }
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
      type: DELETION_STRATEGY_TYPE.DELETE_TRANSACTIONS,
    };

    const confirmation = buildDeletionConfirmationMessage(strategy, t);

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
    totalSelectedCount?: number,
  ): Promise<void> {
    const displayCount = totalSelectedCount ?? eventIds.length;

    const strategy: DeletionStrategy = {
      eventIds,
      type: DELETION_STRATEGY_TYPE.DELETE_EVENTS,
    };

    const confirmation = buildDeletionConfirmationMessage(strategy, t);
    confirmation.message = t('transactions.events.confirmation.delete.message_multiple', {
      count: displayCount,
    });

    await new Promise<void>((resolve) => {
      showConfirm(
        confirmation,
        async () => {
          const result = await deletePartialEvents(eventIds);
          notifyDeletionResult(result.success, displayCount, 'delete', result.message);

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
      type: DELETION_STRATEGY_TYPE.IGNORE_EVENTS,
    };

    const ignoreConfirmation = buildDeletionConfirmationMessage(ignoreStrategy, t);

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

  async function handlePartialSwapDeletion(
    partialSwapGroups: Array<{ groupIds: number[]; selectedIds: number[] }>,
    remainingEventIds: number[],
    transactions: Map<string, TransactionGroup>,
  ): Promise<void> {
    // Collect all event IDs that need to be deleted (including full swap groups)
    const allEventIds = [
      ...partialSwapGroups.flatMap(group => group.groupIds),
      ...remainingEventIds,
    ];

    const strategy: DeletionStrategy = {
      eventIds: allEventIds,
      partialSwapGroups,
      type: DELETION_STRATEGY_TYPE.DELETE_PARTIAL_SWAP,
    };

    const confirmation = buildDeletionConfirmationMessage(strategy, t);

    await new Promise<void>((resolve) => {
      showConfirm(
        confirmation,
        async () => {
          // Delete complete transactions first if any
          let txResult: { message?: string; success: boolean } = { success: true };
          if (transactions.size > 0) {
            txResult = await deleteCompleteTransactions(transactions);
          }

          // Then delete all the events (including full swap groups)
          const eventsResult = await deletePartialEvents(allEventIds);

          const success = txResult.success && eventsResult.success;
          const message = txResult.message || eventsResult.message;
          notifyDeletionResult(success, allEventIds.length, 'delete', message);

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
