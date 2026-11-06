import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/use-selection-mode';
import { get, objectOmit, set } from '@vueuse/shared';
import { all, err, flatMap, ok, type Result } from 'plainfp/result';
import { fromAsync, fromPromise, tap } from 'plainfp/result-async';
import { useConfirm } from '@/modules/core/common/use-confirm';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import { useHistoryEventsActionFailure } from '@/modules/history/events/use-history-events-action-failure';
import { useIgnore } from '@/modules/history/use-ignore';
import { EditKind } from '@/modules/task-center/core/rerun/policy';
import { taskCenterBus } from '@/modules/task-center/events/task-center-bus';
import { buildDeletionConfirmationMessage, DELETION_STRATEGY_TYPE, type DeletionStrategy } from './use-deletion-strategies';
import { analyzeSelectedEvents, type TransactionGroup } from './use-event-analysis';

interface UseHistoryEventsDeletionReturn {
  deleteSelected: () => Promise<void>;
  isDeleting: Readonly<Ref<boolean>>;
}

export function useHistoryEventsDeletion(
  selectionMode: UseHistoryEventsSelectionModeReturn,
  groupedEventsByTxRef: MaybeRefOrGetter<Record<string, HistoryEventRow[]>>,
  originalGroups: MaybeRefOrGetter<HistoryEventRow[]>,
  refreshCallback: () => Promise<void>,
  requestPayload?: ComputedRef<HistoryEventRequestPayload>,
): UseHistoryEventsDeletionReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { ask } = useConfirm();
  const { clear: clearActionFailure, run: runAction } = useHistoryEventsActionFailure();
  const { deleteHistoryEvent: deleteHistoryEventApi, deleteTransactions } = useHistoryEventsApi();
  const { deleteHistoryEvent } = useHistoryEvents();
  const { getChain } = useSupportedChains();

  const { ignoreSingle } = useIgnore<HistoryEventEntry>(
    { toData: item => item.groupIdentifier },
    ref([]),
    refreshCallback,
  );

  const isDeleting = shallowRef<boolean>(false);

  async function deleteCompleteTransactions(
    transactions: Map<string, TransactionGroup>,
  ): Promise<Result<void, unknown>> {
    return fromAsync(async () => {
      for (const [txRef, { chain }] of transactions)
        await deleteTransactions(getChain(chain), txRef);
    }, (error: unknown) => error);
  }

  async function deletePartialEvents(eventIds: number[]): Promise<Result<void, unknown>> {
    if (eventIds.length === 0)
      return ok(undefined);

    return deleteHistoryEvent(eventIds, false);
  }

  /** Excludes each selected event of the transactions from accounting, stopping at the first failure. */
  async function ignoreTransactionEvents(
    transactions: Map<string, TransactionGroup>,
  ): Promise<Result<void, unknown>> {
    for (const [, { events: eventIds, groupIdentifier }] of transactions) {
      const txEvents = groupIdentifier ? toValue(groupedEventsByTxRef)[groupIdentifier] || [] : [];

      const allEvents: HistoryEventEntry[] = txEvents.flat();

      for (const eventId of eventIds) {
        const event = allEvents.find(e => e.identifier === eventId);
        if (!event)
          continue;
        const outcome = await ignoreSingle(event, true);
        if (!outcome.ok)
          return outcome;
      }
    }
    return ok(undefined);
  }

  /**
   * Runs both steps in turn, the second even when the first failed, so one failing half does not
   * leave the other undone.
   *
   * @returns the first step's failure, else the second's
   */
  async function attemptBoth(
    first: () => Promise<Result<void, unknown>>,
    second: () => Promise<Result<void, unknown>>,
  ): Promise<Result<void[], unknown>> {
    const firstOutcome = await first();
    return all([firstOutcome, await second()]);
  }

  /**
   * Settles a delete or an exclusion that worked: the rows changing says so, so selection mode ends
   * and the table is read again.
   */
  async function afterDeletion(): Promise<void> {
    taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_DELETED });
    selectionMode.actions.exit();
    await refreshCallback();
  }

  /**
   * Deletes every event the filter matches.
   *
   * @remarks
   * A backend answering `false` refused without saying why, so the refusal is worded here.
   */
  async function deleteMatching(filter: Parameters<typeof deleteHistoryEventApi>[0]): Promise<Result<void, unknown>> {
    const answer = await fromPromise(deleteHistoryEventApi(filter, true), (error: unknown) => error);
    return flatMap(answer, deleted => (deleted ? ok(undefined) : err(t('transactions.events.delete.error.message'))));
  }

  async function deleteByFilter(totalCount: number): Promise<void> {
    if (!requestPayload) {
      return;
    }

    const filterPayload = get(requestPayload);

    const confirmation = {
      message: t('transactions.events.confirmation.delete.message_all_matching', { count: totalCount }),
      primaryAction: t('common.actions.delete'),
      secondaryAction: t('common.actions.cancel'),
      title: t('transactions.events.confirmation.delete.title'),
    };

    if (await ask(confirmation) !== 'confirm')
      return;

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
    await runAction(t('transactions.events.delete.error.title'), async () => tap(deleteMatching(filterParams), afterDeletion));
  }

  async function deleteSelected(): Promise<void> {
    clearActionFailure();
    const state = get(selectionMode.state);

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
        toValue(originalGroups),
        toValue(groupedEventsByTxRef),
      );

      if (partialSwapGroups.length > 0) {
        await handlePartialSwapDeletion(partialSwapGroups, partialEventIds, completeTransactions);
      }
      else if (completeTransactions.size > 0) {
        await handleCompleteTransactionDeletion(completeTransactions, partialEventIds);
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
  ): Promise<void> {
    const strategy: DeletionStrategy = {
      eventIds: remainingEventIds,
      transactions,
      type: DELETION_STRATEGY_TYPE.DELETE_TRANSACTIONS,
    };

    const confirmation = buildDeletionConfirmationMessage(strategy, t);

    const choice = await ask(confirmation);
    if (choice === 'alternative') {
      await handleIgnoreOption(transactions, remainingEventIds);
      return;
    }
    if (choice !== 'confirm')
      return;

    await runAction(t('transactions.events.delete.error.title'), async () => tap(attemptBoth(
      async () => deleteCompleteTransactions(transactions),
      async () => deletePartialEvents(remainingEventIds),
    ), afterDeletion));
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

    if (await ask(confirmation) !== 'confirm')
      return;

    await runAction(t('transactions.events.delete.error.title'), async () => tap(deletePartialEvents(eventIds), afterDeletion));
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

    if (await ask(ignoreConfirmation) !== 'confirm')
      return;

    await runAction(t('transactions.events.ignore.error.title'), async () => tap(attemptBoth(
      async () => ignoreTransactionEvents(transactions),
      async () => deletePartialEvents(remainingEventIds),
    ), afterDeletion));
  }

  /**
   * Deletes a selection that cuts through a swap.
   *
   * @remarks
   * A swap is only meaningful whole, so selecting any of its legs deletes the group entire. The id
   * list therefore spans every `groupIds` member, not the `selectedIds` the user actually picked.
   */
  async function handlePartialSwapDeletion(
    partialSwapGroups: Array<{ groupIds: number[]; selectedIds: number[] }>,
    remainingEventIds: number[],
    transactions: Map<string, TransactionGroup>,
  ): Promise<void> {
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

    if (await ask(confirmation) !== 'confirm')
      return;

    await runAction(t('transactions.events.delete.error.title'), async () => tap(attemptBoth(
      async () => deleteCompleteTransactions(transactions),
      async () => deletePartialEvents(allEventIds),
    ), afterDeletion));
  }

  return {
    deleteSelected,
    isDeleting: readonly(isDeleting),
  };
}
