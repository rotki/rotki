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

export const isEvmEventType = (type: HistoryEventEntryType): boolean =>
  type === HistoryEventEntryType.EVM_EVENT;

export const isEvmEvent = (event: HistoryEvent): event is EvmHistoryEvent =>
  isEvmEventType(event.entryType);

export const isEvmEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EvmHistoryEvent | undefined> =>
  computed(() => {
    const eventVal = get(event);
    return isEvmEvent(eventVal) ? eventVal : undefined;
  });

export const isWithdrawalEventType = (type: HistoryEventEntryType): boolean =>
  type === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT;

export const isWithdrawalEvent = (
  event: HistoryEvent
): event is EthWithdrawalEvent => isWithdrawalEventType(event.entryType);

export const isWithdrawalEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EthWithdrawalEvent | undefined> =>
  computed(() => {
    const eventVal = get(event);
    return isWithdrawalEvent(eventVal) ? eventVal : undefined;
  });

export const isEthBlockEventType = (type: HistoryEventEntryType): boolean =>
  type === HistoryEventEntryType.ETH_BLOCK_EVENT;

export const isEthBlockEvent = (event: HistoryEvent): event is EthBlockEvent =>
  isEthBlockEventType(event.entryType);

export const isEthBlockEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EthBlockEvent | undefined> =>
  computed(() => {
    const eventVal = get(event);
    return isEthBlockEvent(eventVal) ? eventVal : undefined;
  });

export const isOnlineHistoryEventType = (type: HistoryEventEntryType) =>
  type === HistoryEventEntryType.HISTORY_EVENT;

export const isOnlineHistoryEvent = (
  event: HistoryEvent
): event is OnlineHistoryEvent => isOnlineHistoryEventType(event.entryType);

export const isOnlineHistoryEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<OnlineHistoryEvent | undefined> =>
  computed(() => {
    const eventVal = get(event);
    return isOnlineHistoryEvent(eventVal) ? eventVal : undefined;
  });

export const isEthDepositEventType = (type: HistoryEventEntryType): boolean =>
  type === HistoryEventEntryType.ETH_DEPOSIT_EVENT;

export const isEthDepositEvent = (
  event: HistoryEvent
): event is EthDepositEvent => isEthDepositEventType(event.entryType);

export const isEthDepositEventRef = (
  event: MaybeRef<HistoryEvent>
): ComputedRef<EthDepositEvent | undefined> =>
  computed(() => {
    const eventVal = get(event);
    return isEthDepositEvent(eventVal) ? eventVal : undefined;
  });
