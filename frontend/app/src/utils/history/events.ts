import { type MaybeRef } from '@vueuse/core';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import {
  type EthBlockEvent,
  type EthDepositEvent,
  type EthWithdrawalEvent,
  type EvmHistoryEvent,
  type HistoryEvent,
  type OnlineHistoryEvent
} from '@/types/history/events';

export const isEvmEventType = (
  type: MaybeRef<HistoryEventEntryType>
): boolean => get(type) === HistoryEventEntryType.EVM_EVENT;

export const isEvmEvent = (
  event: MaybeRef<HistoryEvent>
): event is MaybeRef<EvmHistoryEvent> => isEvmEventType(get(event).entryType);

export const isEvmEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EvmHistoryEvent | undefined> =>
  computed(() => (isEvmEvent(event) ? get(event) : undefined));

export const isWithdrawalEventType = (
  type: MaybeRef<HistoryEventEntryType>
): boolean => get(type) === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT;

export const isWithdrawalEvent = (
  event: MaybeRef<HistoryEvent>
): event is MaybeRef<EthWithdrawalEvent> =>
  isWithdrawalEventType(get(event).entryType);

export const isWithdrawalEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EthWithdrawalEvent | undefined> =>
  computed(() => (isWithdrawalEvent(event) ? get(event) : undefined));

export const isEthBlockEventType = (
  type: MaybeRef<HistoryEventEntryType>
): boolean => get(type) === HistoryEventEntryType.ETH_BLOCK_EVENT;

export const isEthBlockEvent = (
  event: MaybeRef<HistoryEvent>
): event is MaybeRef<EthBlockEvent> =>
  isEthBlockEventType(get(event).entryType);

export const isEthBlockEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EthBlockEvent | undefined> =>
  computed(() => (isEthBlockEvent(event) ? get(event) : undefined));

export const isOnlineHistoryEventType = (
  type: MaybeRef<HistoryEventEntryType>
) => get(type) === HistoryEventEntryType.HISTORY_EVENT;

export const isOnlineHistoryEvent = (
  event: MaybeRef<HistoryEvent>
): event is MaybeRef<OnlineHistoryEvent> =>
  isOnlineHistoryEventType(get(event).entryType);

export const isOnlineHistoryEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<OnlineHistoryEvent | undefined> =>
  computed(() => (isOnlineHistoryEvent(event) ? get(event) : undefined));

export const isEthDepositEventType = (
  type: MaybeRef<HistoryEventEntryType>
): boolean => get(type) === HistoryEventEntryType.ETH_DEPOSIT_EVENT;

export const isEthDepositEvent = (
  event: MaybeRef<HistoryEvent>
): event is MaybeRef<EthDepositEvent> =>
  isEthDepositEventType(get(event).entryType);

export const isEthDepositEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EthDepositEvent | undefined> =>
  computed(() => (isEthDepositEvent(event) ? get(event) : undefined));
