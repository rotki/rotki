import type { ComputedRef, Ref } from 'vue';
import type { PullEventPayload } from '@/modules/history/events/event-payloads';
import type {
  EthBlockEvent,
  EvmHistoryEvent,
  EvmSwapEvent,
  HistoryEventEntry,
  SolanaEvent,
  SolanaSwapEvent,
} from '@/modules/history/events/schemas';
import { useReportIssue } from '@/modules/core/common/use-report-issue';
import {
  isEthBlockEvent,
  isEthBlockEventRef,
  isEvmEvent,
  isEvmSwapEvent,
  isOnlineHistoryEvent,
  isSolanaEvent,
  isSolanaSwapEvent,
  toLocationAndTxRef,
} from '@/modules/history/event-utils';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import {
  type DecodableEventType,
  isGroupEditableHistoryEvent,
} from '@/modules/history/management/forms/form-guards';

interface TransactionRef {
  location: string;
  txRef: string;
}

export interface UseHistoryEventActionMenuOptions {
  /** The row the menu belongs to. */
  event: () => HistoryEventEntry;
  /** The other events in the row's group, when the row stands for a group. */
  groupEvents: () => HistoryEventEntry[] | undefined;
  /** Which duplicate bucket the row is in, if any. */
  duplicateHandlingStatus: () => DuplicateHandlingStatus | undefined;
  /** Called once the row's duplicate has been fixed. */
  onFixDuplicate: () => void;
  /** Called once the row has been marked as not a duplicate. */
  onIgnoreDuplicate: () => void;
}

export interface UseHistoryEventActionMenuReturn {
  /** Whether the row's duplicate can be fixed without asking the user to choose. */
  isAutoFixable: ComputedRef<boolean>;
  /** Whether the row is a duplicate that has not been dismissed. */
  isDuplicate: ComputedRef<boolean>;
  /** Whether a fix is in flight. */
  fixLoading: Ref<boolean>;
  /** Whether a dismissal is in flight. */
  ignoreLoading: Ref<boolean>;
  /** Whether a decode of every block event is already running. */
  ethBlockEventsDecoding: Ref<boolean>;
  /** Whether a decode of every transaction is already running. */
  txEventsDecoding: Ref<boolean>;
  /** Whether an event can be added next to this row. */
  canAddEvent: ComputedRef<boolean>;
  /** The row as a block event, when it is one. */
  blockEvent: ComputedRef<EthBlockEvent | undefined>;
  /** The event a re-decode would run on: the row itself, or the first child that can decode. */
  eventWithDecoding: ComputedRef<DecodableEventType | undefined>;
  /** That same event when it is an EVM one, which is the only kind with decode options. */
  decodableEvmEvent: ComputedRef<EvmHistoryEvent | EvmSwapEvent | undefined>;
  /** The transaction the row belongs to, when it belongs to one. */
  eventWithTxRef: ComputedRef<TransactionRef | undefined>;
  /** Whether the row's events can be deleted on their own, without a transaction. */
  canDeleteEvents: ComputedRef<boolean>;
  /** The re-decode request for an event, which a block event names differently. */
  toRedecodePayload: (event: EthBlockEvent | DecodableEventType) => PullEventPayload;
  /** Every event a delete would remove: the whole group, or the row on its own. */
  deletableEventIds: () => number[];
  /** Open the issue reporter, pre-filled with what identifies this row. */
  openReportDialog: () => void;
  /** Ask before fixing the row's duplicate. */
  confirmFixDuplicate: () => void;
  /** Ask before marking the row as not a duplicate. */
  confirmIgnoreDuplicate: () => void;
}

/**
 * Everything the row's action menu has to work out about its event: which actions apply, what
 * they act on, and what each request looks like.
 *
 * ⚠️ A row is not always the event an action runs on: a re-decode runs on the first decodable event
 * in the group (possibly a child), a delete removes the whole group, and a block event names its
 * re-decode by block number where everything else names it by location and transaction reference.
 */
export function useHistoryEventActionMenu(
  options: UseHistoryEventActionMenuOptions,
): UseHistoryEventActionMenuReturn {
  const { duplicateHandlingStatus, event, groupEvents, onFixDuplicate, onIgnoreDuplicate } = options;

  const { t } = useI18n({ useScope: 'global' });
  const { ethBlockEventsDecoding, txEventsDecoding } = useHistoryEventsStatus();
  const { show: showReportIssue } = useReportIssue();
  const {
    confirmAndFixDuplicate,
    confirmAndMarkNonDuplicated,
    fixLoading,
    ignoreLoading,
  } = useCustomizedEventDuplicates();

  const isAutoFixable = computed<boolean>(() => duplicateHandlingStatus() === DuplicateHandlingStatus.AUTO_FIX);

  const isDuplicate = computed<boolean>(() => {
    const status = duplicateHandlingStatus();
    return !!status && status !== DuplicateHandlingStatus.IGNORED;
  });

  const canAddEvent = computed<boolean>(() => !isGroupEditableHistoryEvent(event()));

  const evmEvent = computed<EvmHistoryEvent | EvmSwapEvent | undefined>(() => {
    const row = event();
    if (isEvmSwapEvent(row) || isEvmEvent(row))
      return row;

    return undefined;
  });

  const solanaEvent = computed<SolanaEvent | SolanaSwapEvent | undefined>(() => {
    const row = event();
    if (isSolanaSwapEvent(row) || isSolanaEvent(row))
      return row;

    return undefined;
  });

  const eventWithDecoding = computed<DecodableEventType | undefined>(() => {
    const direct = get(evmEvent) ?? get(solanaEvent);
    if (direct)
      return direct;

    const children = groupEvents();
    if (!children)
      return undefined;

    for (const child of children) {
      if (isEvmEvent(child) || isEvmSwapEvent(child) || isSolanaEvent(child) || isSolanaSwapEvent(child))
        return child;
    }

    return undefined;
  });

  const decodableEvmEvent = computed<EvmHistoryEvent | EvmSwapEvent | undefined>(() => {
    const decoded = get(eventWithDecoding);
    if (decoded && (isEvmEvent(decoded) || isEvmSwapEvent(decoded)))
      return decoded;

    return undefined;
  });

  const eventWithTxRef = computed<TransactionRef | undefined>(() => {
    const evm = get(evmEvent);
    if (evm)
      return { location: evm.location, txRef: evm.txRef };

    const solana = get(solanaEvent);
    if (solana)
      return { location: solana.location, txRef: solana.txRef };

    const row = event();
    if (isOnlineHistoryEvent(row) && 'txRef' in row && row.txRef)
      return { location: row.location, txRef: row.txRef };

    return undefined;
  });

  const blockEvent = isEthBlockEventRef(() => event());

  const canDeleteEvents = computed<boolean>(() => !get(eventWithTxRef) && !get(blockEvent));

  function toRedecodePayload(target: EthBlockEvent | DecodableEventType): PullEventPayload {
    if (isEthBlockEvent(target)) {
      return {
        data: [target.blockNumber],
        type: target.entryType,
      };
    }

    return {
      data: toLocationAndTxRef(target),
      type: target.entryType,
    };
  }

  function deletableEventIds(): number[] {
    return groupEvents()?.map(child => child.identifier) ?? [event().identifier];
  }

  function openReportDialog(): void {
    const row = event();
    const txRef = get(eventWithTxRef)?.txRef;

    const description = [
      t('actions.history_events.report_issue.description_intro'),
      txRef ? t('actions.history_events.report_issue.tx_hash', { hash: txRef }) : '',
      t('actions.history_events.report_issue.location', { location: row.location }),
      '',
      t('actions.history_events.report_issue.more_detail'),
      t('actions.history_events.report_issue.placeholder'),
    ].filter(Boolean).join('\n');

    showReportIssue({
      description,
      title: t('actions.history_events.report_issue.title'),
    });
  }

  function confirmFixDuplicate(): void {
    const groupIdentifier = event().groupIdentifier;
    if (!groupIdentifier)
      return;

    confirmAndFixDuplicate([groupIdentifier], onFixDuplicate);
  }

  function confirmIgnoreDuplicate(): void {
    const groupIdentifier = event().groupIdentifier;
    if (!groupIdentifier)
      return;

    confirmAndMarkNonDuplicated([groupIdentifier], onIgnoreDuplicate);
  }

  return {
    blockEvent,
    canAddEvent,
    canDeleteEvents,
    confirmFixDuplicate,
    confirmIgnoreDuplicate,
    decodableEvmEvent,
    deletableEventIds,
    ethBlockEventsDecoding,
    eventWithDecoding,
    eventWithTxRef,
    fixLoading,
    ignoreLoading,
    isAutoFixable,
    isDuplicate,
    openReportDialog,
    toRedecodePayload,
    txEventsDecoding,
  };
}
