import type { ComputedRef, Ref } from 'vue';
import type {
  LinkedMovementMatch,
  LocationAndTxRef,
  PullEventPayload,
} from '@/modules/history/events/event-payloads';
import type {
  HistoryEventEntry,
  HistoryEventRow,
} from '@/modules/history/events/schemas';
import type { HistoryEventDeletePayload, HistoryEventsTableEmitFn } from '@/modules/history/events/types';
import { HistoryEventEntryType } from '@rotki/common';
import { tap } from 'plainfp/result-async';
import { Defaults } from '@/modules/core/common/defaults';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { isAssetMovementEvent, isCustomizedEvent } from '@/modules/history/event-utils';
import { useCompleteEvents } from '@/modules/history/events/use-complete-events';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';
import { useHistoryEventsActionFailure } from '@/modules/history/events/use-history-events-action-failure';
import { useIgnore } from '@/modules/history/use-ignore';
import { EditKind } from '@/modules/task-center/core/rerun/policy';
import { taskCenterBus } from '@/modules/task-center/events/task-center-bus';

interface UseHistoryEventsOperationsOptions {
  /** Events per group identifier including ignored-asset ones, so redecode acts on the full group rather than what the table shows. */
  completeEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
  /** Flat list of all loaded events, scanned to find the highest sequence index within a group when suggesting the next one. */
  flattenedEvents: ComputedRef<HistoryEventEntry[]>;
}

interface UseHistoryEventsOperationsReturn {
  modelShowRedecodeConfirmation: Ref<boolean>;
  redecodePayload: Readonly<Ref<PullEventPayload | undefined>>;
  hasCustomEvents: Readonly<Ref<boolean>>;
  showIndexerOptions: Readonly<Ref<boolean>>;

  getItemClass: (item: HistoryEventEntry) => '' | 'opacity-50';
  /** Ignores or deletes what the row's menu already asked about; a failure is named above the table. */
  deleteEvents: (payload: HistoryEventDeletePayload) => Promise<void>;
  suggestNextSequenceId: (group: HistoryEventEntry) => string;
  /** Deletes a transaction and its events, once the row's menu asked; a failure is named above the table. */
  deleteTransaction: (payload: LocationAndTxRef) => Promise<void>;
  redecode: (payload: PullEventPayload, eventIdentifier: string) => void;
  redecodeWithOptions: (payload: PullEventPayload, groupIdentifier: string) => void;
  confirmRedecode: (event: { payload: PullEventPayload; deleteCustom: boolean; customIndexersOrder?: string[] }) => void;
  toggle: (event: HistoryEventEntry) => Promise<void>;
}

export function useHistoryEventsOperations(
  options: UseHistoryEventsOperationsOptions,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsOperationsReturn {
  const { completeEventsMapped, flattenedEvents } = options;
  const { getGroupEvents } = useCompleteEvents(completeEventsMapped);

  const selected = ref<HistoryEventEntry[]>([]);
  const modelShowRedecodeConfirmation = shallowRef<boolean>(false);
  const redecodePayload = ref<PullEventPayload>();
  const hasCustomEvents = shallowRef<boolean>(false);
  const showIndexerOptions = shallowRef<boolean>(false);
  const pendingLinkedMovement = ref<LinkedMovementMatch>();

  const { t } = useI18n({ useScope: 'global' });

  const { run: runAction } = useHistoryEventsActionFailure();
  const { getChain } = useSupportedChains();

  const { deleteTransactions } = useHistoryEventsApi();
  const { deleteHistoryEvent } = useHistoryEvents();
  const { ignoreSingle, toggle: toggleIgnore } = useIgnore<HistoryEventEntry>({
    toData: (item: HistoryEventEntry) => item.groupIdentifier,
  }, selected, () => {
    emit('refresh');
  });

  function buildLinkedMovement(movementEvent: HistoryEventEntry, groupEvents: HistoryEventEntry[]): LinkedMovementMatch {
    const nonMovementEvents = groupEvents.filter(item => !isAssetMovementEvent(item) && item.eventSubtype !== 'fee');
    const movementTimestamp = movementEvent.timestamp;
    const movementAmount = movementEvent.amount;

    const defaultTimeRange = Defaults.ASSET_MOVEMENT_TIME_RANGE;
    const defaultTolerance = Defaults.ASSET_MOVEMENT_AMOUNT_TOLERANCE;

    let timeRange: number = defaultTimeRange;
    let tolerance: string = defaultTolerance;

    if (nonMovementEvents.length > 0) {
      const timeDiffs = nonMovementEvents.map(e => Math.abs(e.timestamp - movementTimestamp));
      timeRange = Math.max(Math.max(...timeDiffs, 60) * 2, defaultTimeRange);

      const amountDiffs = nonMovementEvents
        .map(e => movementAmount.minus(e.amount).abs().div(movementAmount))
        .filter(d => d.isFinite());

      if (amountDiffs.length > 0) {
        const maxDiff = amountDiffs.reduce((a, b) => (a.gt(b) ? a : b));
        const computed = maxDiff.multipliedBy(2).toFixed(6);
        tolerance = computed > defaultTolerance ? computed : defaultTolerance;
      }
    }

    return {
      groupIdentifier: movementEvent.actualGroupIdentifier ?? movementEvent.groupIdentifier,
      identifier: movementEvent.identifier,
      timeRange,
      tolerance,
    };
  }

  /**
   * The strip title for a failed exclusion from accounting, or a failed inclusion.
   *
   * @param excluded - whether it tried to exclude rather than include
   */
  function ignoreFailureTitle(excluded: boolean): string {
    return excluded ? t('actions.ignore.error.title') : t('actions.unignore.error.title');
  }

  async function toggle(event: HistoryEventEntry): Promise<void> {
    await runAction(ignoreFailureTitle(!event.ignoredInAccounting), async () => toggleIgnore(event));
  }

  function getItemClass(item: HistoryEventEntry): '' | 'opacity-50' {
    return item.ignoredInAccounting ? 'opacity-50' : '';
  }

  async function deleteEvents(payload: HistoryEventDeletePayload): Promise<void> {
    if (payload.type === 'ignore') {
      await runAction(ignoreFailureTitle(true), async () => ignoreSingle(payload.event, true));
      return;
    }

    await runAction(t('transactions.events.delete.error.title'), async () => tap(deleteHistoryEvent(payload.ids), () => {
      emit('refresh');
      taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_DELETED });
    }));
  }

  function suggestNextSequenceId(group: HistoryEventEntry): string {
    const allFlattened = get(flattenedEvents);

    if (!allFlattened?.length)
      return (Number(group.sequenceIndex) + 1).toString();

    const groupIdentifierHeader = group.groupIdentifier;
    const filtered = allFlattened
      .filter(({ groupIdentifier, hidden }) => groupIdentifier === groupIdentifierHeader && !hidden)
      .map(({ sequenceIndex }) => Number(sequenceIndex))
      .sort((a, b) => b - a);

    return ((filtered[0] ?? Number(group.sequenceIndex)) + 1).toString();
  }

  async function deleteTransaction({ location, txRef }: LocationAndTxRef): Promise<void> {
    await runAction(t('transactions.dialog.delete.error.title'), async () => {
      await deleteTransactions(getChain(location), txRef);
      emit('refresh');
      taskCenterBus.emit('event:mutated', { kind: EditKind.TRANSACTION_DELETED });
    });
  }

  function isEvmPayload(payload: PullEventPayload): boolean {
    return payload.type === HistoryEventEntryType.EVM_EVENT
      || payload.type === HistoryEventEntryType.EVM_SWAP_EVENT;
  }

  /**
   * Tells the task center that a redecode rewrote a group's events, so it can offer to recompute
   * the profit and loss report and the historical balances that just went stale.
   *
   * @remarks
   * Call it only where a redecode is actually emitted. Calling it where the confirmation dialog is
   * merely opened would offer a recompute for a redecode the user may still cancel.
   */
  function notifyRedecoded(): void {
    taskCenterBus.emit('event:mutated', { kind: EditKind.EVENT_REDECODED });
  }

  function redecode(payload: PullEventPayload, groupIdentifier: string): void {
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', { blockNumbers: payload.data });
      notifyRedecoded();
      return;
    }

    const groupEvents = getGroupEvents(groupIdentifier);
    const isAnyCustom = groupEvents.some(item => isCustomizedEvent(item));
    const movementEvent = groupEvents.find(item => isAssetMovementEvent(item));

    // If there are custom events, show dialog to ask about custom event handling
    if (isAnyCustom) {
      set(hasCustomEvents, true);
      set(showIndexerOptions, false);
      set(redecodePayload, payload);
      set(modelShowRedecodeConfirmation, true);
      return;
    }

    // No custom events - just redecode directly without dialog
    emit('refresh', {
      deleteCustom: false,
      linkedMovement: movementEvent ? buildLinkedMovement(movementEvent, groupEvents) : undefined,
      transactions: [payload.data],
    });
    notifyRedecoded();
  }

  function redecodeWithOptions(payload: PullEventPayload, eventIdentifier: string): void {
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', { blockNumbers: payload.data });
      notifyRedecoded();
      return;
    }

    const groupEvents = getGroupEvents(eventIdentifier);
    const isAnyCustom = groupEvents.some(item => isCustomizedEvent(item));
    const movementEvent = groupEvents.find(item => isAssetMovementEvent(item));
    set(pendingLinkedMovement, movementEvent ? buildLinkedMovement(movementEvent, groupEvents) : undefined);

    set(hasCustomEvents, isAnyCustom);
    set(showIndexerOptions, isEvmPayload(payload));
    set(redecodePayload, payload);
    set(modelShowRedecodeConfirmation, true);
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
        linkedMovement: get(pendingLinkedMovement),
        transactions: [payload.data],
      });
    }
    notifyRedecoded();
    set(redecodePayload, undefined);
    set(pendingLinkedMovement, undefined);
  }

  return {
    confirmRedecode,
    deleteEvents,
    deleteTransaction,
    getItemClass,
    hasCustomEvents: readonly(hasCustomEvents),
    redecode,
    redecodePayload: shallowReadonly(redecodePayload),
    redecodeWithOptions,
    showIndexerOptions: readonly(showIndexerOptions),
    modelShowRedecodeConfirmation,
    suggestNextSequenceId,
    toggle,
  };
}
