import type { ComputedRef, Ref } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { get, objectOmit, set } from '@vueuse/shared';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useIgnore } from '@/composables/history';
import { useHistoryEvents } from '@/composables/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
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
  pageParams?: ComputedRef<HistoryEventRequestPayload>,
): UseHistoryEventsDeletionReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { show: showConfirm } = useConfirmStore();
  const { setMessage } = useMessageStore();
  const { deleteHistoryEvent: deleteHistoryEventApi, deleteTransactions } = useHistoryEventsApi();
  const { deleteHistoryEvent } = useHistoryEvents();
  const { getChain } = useSupportedChains();

  const { ignoreSingle } = useIgnore<HistoryEventEntry>(
    { toData: item => item.groupIdentifier },
    ref([]),
    refreshCallback,
  );

  const isDeleting = ref<boolean>(false);

  async function deleteCompleteTransactions(
    transactions: Map<string, TransactionGroup>,
  ): Promise<{ message?: string; success: boolean }> {
    try {
      for (const [txRef, { chain }] of transactions)
        await deleteTransactions(getChain(chain), txRef);

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
      for (const [, { events: eventIds, groupIdentifier }] of transactions) {
        // Use groupIdentifier to look up the events
        const txEvents = groupIdentifier ? get(groupedEventsByTxRef)[groupIdentifier] || [] : [];

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

  function showDeletionResult(
    success: boolean,
    count: number,
    type: 'delete' | 'ignore',
    message?: string,
    isGroupCount = false,
  ): void {
    const title = type === 'delete'
      ? t('transactions.events.delete.title')
      : t('transactions.events.ignore.title');

    let successMessage: string;
    if (type === 'delete') {
      successMessage = isGroupCount
        ? t('transactions.events.delete.success_groups', { count }, count)
        : t('transactions.events.delete.success', { count }, count);
    }
    else {
      successMessage = t('transactions.events.ignore.success', { count }, count);
    }

    const errorTitle = type === 'delete'
      ? t('transactions.events.delete.error.title')
      : t('transactions.events.ignore.error.title');

    const errorMessage = type === 'delete'
      ? message || t('transactions.events.delete.error.message')
      : message || t('transactions.events.ignore.error.message');

    setMessage({
      description: success ? successMessage : errorMessage,
      success,
      title: success ? title : errorTitle,
    });
  }

  async function deleteByFilter(totalCount: number): Promise<void> {
    if (!pageParams) {
      return;
    }

    const filterPayload = get(pageParams);

    const confirmation = {
      message: t('transactions.events.confirmation.delete.message_all_matching', { count: totalCount }),
      primaryAction: t('common.actions.delete'),
      secondaryAction: t('common.actions.cancel'),
      title: t('transactions.events.confirmation.delete.title'),
    };

    await new Promise<void>((resolve) => {
      showConfirm(
        confirmation,
        async () => {
          try {
            // Remove pagination and sorting params for filter-based deletion
            const filterParams = objectOmit(filterPayload, [
              'aggregateByGroupIds',
              'ascending',
              'ignoreCache',
              'limit',
              'offset',
              'onlyCache',
              'orderByAttributes',
            ]);
            const result = await deleteHistoryEventApi(filterParams, true);
            showDeletionResult(result, totalCount, 'delete', undefined, true);

            if (result) {
              selectionMode.actions.exit();
              await refreshCallback();
            }
          }
          catch (error: any) {
            showDeletionResult(false, totalCount, 'delete', error.message, true);
          }
          resolve();
        },
      );
    });
  }

  async function deleteSelected(): Promise<void> {
    const state = get(selectionMode.state);

    // Handle select all matching case
    if (state.selectAllMatching) {
      set(isDeleting, true);
      try {
        await deleteByFilter(state.totalMatchingCount);
      }
      finally {
        set(isDeleting, false);
      }
      return;
    }

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
          showDeletionResult(success, totalCount, 'delete', message);

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
          showDeletionResult(result.success, displayCount, 'delete', result.message);

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
          showDeletionResult(success, transactions.size, 'ignore', message);

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
          showDeletionResult(success, allEventIds.length, 'delete', message);

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
