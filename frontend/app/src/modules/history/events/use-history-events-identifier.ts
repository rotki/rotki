import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { type MessageKey, msg } from '@/message-key';
import {
  isAssetMovementEventRef,
  isEthBlockEventRef,
  isWithdrawalEventRef,
} from '@/modules/history/event-utils';

/**
 * Header message per entry type.
 *
 * @remarks
 * Exhaustive on purpose: deriving the key with `toSnakeCase(entryType)` meant a new entry type
 * produced a key nobody had written, and `i18n-t` renders a missing keypath verbatim, so bitcoin
 * and solana events displayed the raw `transactions.events.headers.*` string. Spelling the map out
 * fails the build instead, and the branded values are checked against the locale messages.
 */
const HEADER_KEYS: Record<HistoryEventEntryType, MessageKey> = {
  [HistoryEventEntryType.ASSET_MOVEMENT_EVENT]: msg.$t('transactions.events.headers.asset_movement_event'),
  [HistoryEventEntryType.BITCOIN_EVENT]: msg.$t('transactions.events.headers.bitcoin_event'),
  [HistoryEventEntryType.ETH_BLOCK_EVENT]: msg.$t('transactions.events.headers.eth_block_event'),
  [HistoryEventEntryType.ETH_DEPOSIT_EVENT]: msg.$t('transactions.events.headers.eth_deposit_event'),
  [HistoryEventEntryType.ETH_WITHDRAWAL_EVENT]: msg.$t('transactions.events.headers.eth_withdrawal_event'),
  [HistoryEventEntryType.EVM_EVENT]: msg.$t('transactions.events.headers.evm_event'),
  [HistoryEventEntryType.EVM_SWAP_EVENT]: msg.$t('transactions.events.headers.evm_swap_event'),
  [HistoryEventEntryType.HISTORY_EVENT]: msg.$t('transactions.events.headers.history_event'),
  [HistoryEventEntryType.SOLANA_EVENT]: msg.$t('transactions.events.headers.solana_event'),
  [HistoryEventEntryType.SOLANA_SWAP_EVENT]: msg.$t('transactions.events.headers.solana_swap_event'),
  [HistoryEventEntryType.SWAP_EVENT]: msg.$t('transactions.events.headers.swap_event'),
};

/** Entry types that carry a `txRef` yet keep their own header rather than the generic EVM one. */
const SPECIAL_TYPES_WITH_TX_REF: HistoryEventEntryType[] = [
  HistoryEventEntryType.ETH_DEPOSIT_EVENT,
  HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
];

/** A transaction reference and the location it belongs to, as the hash links render it. */
interface LocatedTxRef {
  location: string;
  txRef: string;
}

interface UseHistoryEventsIdentifierReturn {
  /** Every distinct transaction reference in the group, for an asset movement; empty otherwise. */
  allTxRefs: ComputedRef<LocatedTxRef[]>;
  /** The event narrowed to an asset movement, or undefined when it is not one. */
  assetMovementEvent: ReturnType<typeof isAssetMovementEventRef>;
  /** The movement's own transaction id from its extra data, when it carries one. */
  assetMovementTransactionId: ComputedRef<string | undefined>;
  /** The event narrowed to an eth block event, or undefined when it is not one. */
  blockEvent: ReturnType<typeof isEthBlockEventRef>;
  /** How many references beyond the first the group holds, for the "+N" affordance. */
  extraHashCount: ComputedRef<number>;
  /** The event's own transaction reference, when it has one. */
  eventWithTxRef: ComputedRef<LocatedTxRef | undefined>;
  /**
   * Which identifier shape is being rendered, or undefined when none applies.
   *
   * @remarks
   * Used as a render key. Without it a block event's identifier could be reused to display a hash
   * event's, showing a number where a hash belongs.
   */
  key: ComputedRef<'tx_hash' | 'block' | 'withdraw' | 'asset_movement' | undefined>;
  /** Characters of a hash to show before truncating, widening with the viewport. */
  truncateLength: ComputedRef<number>;
  /**
   * The header message for this event.
   *
   * @remarks
   * An event carrying a `txRef` reads as an EVM event unless its own type is listed in
   * {@link SPECIAL_TYPES_WITH_TX_REF}, which is how an evm swap borrows the evm header.
   */
  translationKey: ComputedRef<MessageKey>;
  /** The event narrowed to a withdrawal, or undefined when it is not one. */
  withdrawEvent: ReturnType<typeof isWithdrawalEventRef>;
}

/**
 * Derives everything the identifier cell renders from one event and, optionally, its group.
 *
 * @param event - the event whose identifier is being rendered
 * @param groupEvents - the events sharing its group, needed only to collect an asset movement's
 * transaction references
 * @returns the derived values; nothing here has side effects
 */
export function useHistoryEventsIdentifier(
  event: MaybeRefOrGetter<HistoryEventEntry>,
  groupEvents: MaybeRefOrGetter<HistoryEventEntry[] | undefined>,
): UseHistoryEventsIdentifierReturn {
  const { is2xlAndUp, isMd } = useBreakpoint();

  const blockEvent = isEthBlockEventRef(() => toValue(event));
  const withdrawEvent = isWithdrawalEventRef(() => toValue(event));
  const assetMovementEvent = isAssetMovementEventRef(() => toValue(event));

  const truncateLength = computed<number>(() => {
    if (get(is2xlAndUp))
      return 12;

    if (get(isMd))
      return 6;

    return 8;
  });

  const eventWithTxRef = computed<LocatedTxRef | undefined>(() => {
    const current = toValue(event);
    if ('txRef' in current && current.txRef) {
      return {
        location: current.location,
        txRef: current.txRef,
      };
    }
    return undefined;
  });

  const allTxRefs = computed<LocatedTxRef[]>(() => {
    const group = toValue(groupEvents);
    if (!get(assetMovementEvent) || !group)
      return [];

    const seen = new Set<string>();
    const result: LocatedTxRef[] = [];

    for (const child of group) {
      if (!('txRef' in child) || !child.txRef || seen.has(child.txRef))
        continue;

      seen.add(child.txRef);
      result.push({
        location: child.location,
        txRef: child.txRef,
      });
    }

    return result;
  });

  const extraHashCount = computed<number>(() => Math.max(get(allTxRefs).length - 1, 0));

  const translationKey = computed<MessageKey>(() => {
    let entryType = toValue(event).entryType;

    if (get(eventWithTxRef) && !SPECIAL_TYPES_WITH_TX_REF.includes(entryType))
      entryType = HistoryEventEntryType.EVM_EVENT;

    return HEADER_KEYS[entryType];
  });

  const assetMovementTransactionId = computed<string | undefined>(
    () => get(assetMovementEvent)?.extraData?.transactionId ?? undefined,
  );

  const key = computed<'tx_hash' | 'block' | 'withdraw' | 'asset_movement' | undefined>(() => {
    if (get(eventWithTxRef))
      return 'tx_hash';
    if (get(blockEvent))
      return 'block';
    if (get(withdrawEvent))
      return 'withdraw';
    if (get(assetMovementEvent))
      return 'asset_movement';
    return undefined;
  });

  return {
    allTxRefs,
    assetMovementEvent,
    assetMovementTransactionId,
    blockEvent,
    eventWithTxRef,
    extraHashCount,
    key,
    translationKey,
    truncateLength,
    withdrawEvent,
  };
}
