import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventDeletePayload, HistoryEventsTableEmitFn, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import type {
  LinkedMovementMatch,
  LocationAndTxRef,
  PullEventPayload,
} from '@/types/history/events';
import type {
  HistoryEventEntry,
  HistoryEventRow,
} from '@/types/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useAssetMovementMatchingApi } from '@/composables/api/history/events/asset-movement-matching';
import { useIgnore } from '@/composables/history';
import { useHistoryEvents } from '@/composables/history/events';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import { useSupportedChains } from '@/composables/info/chains';
import { Defaults } from '@/data/defaults';
import { useCompleteEvents } from '@/modules/history/events/composables/use-complete-events';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { isTaskCancelled } from '@/utils';
import { isAssetMovementEvent, isCustomizedEvent } from '@/utils/history/events';

interface UseHistoryEventsOperationsOptions {
  completeEventsMapped: ComputedRef<Record<string, HistoryEventRow[]>>;
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
  confirmUnlink: (payload: HistoryEventUnlinkPayload) => void;
  unlinkGroup: (groupId: string) => void;
  suggestNextSequenceId: (group: HistoryEventEntry) => string;
  confirmTxAndEventsDelete: (payload: LocationAndTxRef) => void;
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
  const showRedecodeConfirmation = ref<boolean>(false);
  const redecodePayload = ref<PullEventPayload>();
  const hasCustomEvents = ref<boolean>(false);
  const showIndexerOptions = ref<boolean>(false);
  const pendingLinkedMovement = ref<LinkedMovementMatch>();

  const { t } = useI18n({ useScope: 'global' });

  const { notify } = useNotificationsStore();
  const { show } = useConfirmStore();
  const { getChain } = useSupportedChains();

  const { deleteTransactions } = useHistoryEventsApi();
  const { unlinkAssetMovement } = useAssetMovementMatchingApi();
  const { refreshUnmatchedAssetMovements } = useUnmatchedAssetMovements();
  const { deleteHistoryEvent } = useHistoryEvents();
  const { ignoreSingle, toggle } = useIgnore<HistoryEventEntry>({
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
      groupIdentifier: movementEvent.actualGroupIdentifier || movementEvent.groupIdentifier,
      identifier: movementEvent.identifier,
      timeRange,
      tolerance,
    };
  }

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

  function confirmUnlink(payload: HistoryEventUnlinkPayload): void {
    show({
      message: t('transactions.events.confirmation.unlink.message'),
      primaryAction: t('common.actions.confirm'),
      title: t('transactions.events.confirmation.unlink.title'),
    }, async () => onConfirmUnlink(payload));
  }

  async function onConfirmUnlink(payload: HistoryEventUnlinkPayload): Promise<void> {
    try {
      await unlinkAssetMovement(payload.identifier);
      await refreshUnmatchedAssetMovements();
      emit('refresh');
    }
    catch (error: any) {
      notify({
        display: true,
        message: error.message,
        title: t('transactions.events.unlink_error'),
      });
    }
  }

  function unlinkGroup(groupId: string): void {
    const events = getGroupEvents(groupId);
    const event = events.find(item => isAssetMovementEvent(item) && item.eventSubtype !== 'fee' && !!item.actualGroupIdentifier);
    if (event) {
      confirmUnlink({ identifier: event.identifier });
    }
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

  function redecode(payload: PullEventPayload, groupIdentifier: string): void {
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', { blockNumbers: payload.data });
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
      set(showRedecodeConfirmation, true);
      return;
    }

    // No custom events - just redecode directly without dialog
    emit('refresh', {
      deleteCustom: false,
      linkedMovement: movementEvent ? buildLinkedMovement(movementEvent, groupEvents) : undefined,
      transactions: [payload.data],
    });
  }

  function redecodeWithOptions(payload: PullEventPayload, eventIdentifier: string): void {
    if (payload.type === HistoryEventEntryType.ETH_BLOCK_EVENT) {
      emit('refresh:block-event', { blockNumbers: payload.data });
      return;
    }

    const groupEvents = getGroupEvents(eventIdentifier);
    const isAnyCustom = groupEvents.some(item => isCustomizedEvent(item));
    const movementEvent = groupEvents.find(item => isAssetMovementEvent(item));
    set(pendingLinkedMovement, movementEvent ? buildLinkedMovement(movementEvent, groupEvents) : undefined);

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
        linkedMovement: get(pendingLinkedMovement),
        transactions: [payload.data],
      });
    }
    set(redecodePayload, undefined);
    set(pendingLinkedMovement, undefined);
  }

  return {
    confirmDelete,
    confirmRedecode,
    confirmTxAndEventsDelete,
    confirmUnlink,
    getItemClass,
    unlinkGroup,
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
