import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import {
  type AssetMovementEvent,
  type EthBlockEvent,
  type EthDepositEvent,
  type EthWithdrawalEvent,
  type EvmHistoryEvent,
  type HistoryEvent,
  HistoryEventAccountingRuleStatus,
  type HistoryEventEntry,
  type OnlineHistoryEvent,
} from '@/types/history/events';
import { HistoryEventEntryType } from '@rotki/common';

export function isOfEventType<T extends HistoryEvent>(e: HistoryEvent, type: HistoryEventEntryType): e is T {
  return type === e?.entryType;
}

export function isEvmEventType(type: HistoryEventEntryType): boolean {
  return type === HistoryEventEntryType.EVM_EVENT;
}

export function isEvmEvent(event: HistoryEvent): event is EvmHistoryEvent {
  return isEvmEventType(event.entryType);
}

export function isEvmEventRef(event: MaybeRef<HistoryEvent>): ComputedRef<EvmHistoryEvent | undefined> {
  return computed(() => {
    const eventVal = get(event);
    return isEvmEvent(eventVal) ? eventVal : undefined;
  });
}

export function isWithdrawalEventType(type: HistoryEventEntryType): boolean {
  return type === HistoryEventEntryType.ETH_WITHDRAWAL_EVENT;
}

export function isWithdrawalEvent(event: HistoryEvent): event is EthWithdrawalEvent {
  return isWithdrawalEventType(event.entryType);
}

export function isWithdrawalEventRef(event: MaybeRef<HistoryEvent>): ComputedRef<EthWithdrawalEvent | undefined> {
  return computed(() => {
    const eventVal = get(event);
    return isWithdrawalEvent(eventVal) ? eventVal : undefined;
  });
}

export function isEthBlockEventType(type: HistoryEventEntryType): boolean {
  return type === HistoryEventEntryType.ETH_BLOCK_EVENT;
}

export function isEthBlockEvent<T extends HistoryEvent>(event: T): event is T & EthBlockEvent {
  return isEthBlockEventType(event.entryType);
}

export function isEthBlockEventRef(event: MaybeRef<HistoryEvent>): ComputedRef<EthBlockEvent | undefined> {
  return computed(() => {
    const eventVal = get(event);
    return isEthBlockEvent(eventVal) ? eventVal : undefined;
  });
}

export function isOnlineHistoryEventType(type: HistoryEventEntryType): boolean {
  return type === HistoryEventEntryType.HISTORY_EVENT;
}

export function isOnlineHistoryEvent(event: HistoryEvent): event is OnlineHistoryEvent {
  return isOnlineHistoryEventType(event.entryType);
}

export function isEthDepositEventType(type: HistoryEventEntryType): boolean {
  return type === HistoryEventEntryType.ETH_DEPOSIT_EVENT;
}

export function isEthDepositEvent(event: HistoryEvent): event is EthDepositEvent {
  return isEthDepositEventType(event.entryType);
}

export function isEthDepositEventRef(event: MaybeRef<HistoryEvent>): ComputedRef<EthDepositEvent | undefined> {
  return computed(() => {
    const eventVal = get(event);
    return isEthDepositEvent(eventVal) ? eventVal : undefined;
  });
}

export function isAssetMovementEventType(type: HistoryEventEntryType): boolean {
  return type === HistoryEventEntryType.ASSET_MOVEMENT_EVENT;
}

export function isAssetMovementEvent(event: HistoryEvent): event is AssetMovementEvent {
  return isAssetMovementEventType(event.entryType);
}

export function isAssetMovementEventRef(event: MaybeRef<HistoryEvent>): ComputedRef<AssetMovementEvent | undefined> {
  return computed(() => {
    const eventVal = get(event);
    return isAssetMovementEvent(eventVal) ? eventVal : undefined;
  });
}

export function isMissingAccountingRule(type: HistoryEventAccountingRuleStatus): boolean {
  return type === HistoryEventAccountingRuleStatus.NOT_PROCESSED;
}

export function isEventMissingAccountingRule(event: HistoryEventEntry): boolean {
  return isMissingAccountingRule(event.eventAccountingRuleStatus);
}

export function isAccountingRuleProcessed(type: HistoryEventAccountingRuleStatus): boolean {
  return type === HistoryEventAccountingRuleStatus.PROCESSED;
}

export function isEventAccountingRuleProcessed(event: HistoryEventEntry): boolean {
  return isAccountingRuleProcessed(event.eventAccountingRuleStatus);
}
