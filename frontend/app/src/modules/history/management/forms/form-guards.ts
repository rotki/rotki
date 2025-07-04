import type {
  EvmSwapEvent,
  GroupEditableHistoryEvents,
  HistoryEvent,
  SwapEvent,
} from '@/types/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';

export function isGroupEditableHistoryEvent(event: HistoryEvent): event is GroupEditableHistoryEvents {
  return event.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT
    || event.entryType === HistoryEventEntryType.SWAP_EVENT;
}

export function isSwapEvent(event: HistoryEvent): event is SwapEvent {
  return event.entryType === HistoryEventEntryType.SWAP_EVENT;
}

export function isEvmSwapEvent(event: HistoryEvent): event is EvmSwapEvent {
  return event.entryType === HistoryEventEntryType.EVM_SWAP_EVENT;
}

export const EVM_EVENTS = [
  HistoryEventEntryType.EVM_EVENT,
  HistoryEventEntryType.EVM_SWAP_EVENT,
] as const;

export function isEvmTypeEvent(type: HistoryEventEntryType): boolean {
  return Array.prototype.includes.call(EVM_EVENTS, type);
}

export const SWAP_EVENTS = [
  HistoryEventEntryType.SWAP_EVENT,
  HistoryEventEntryType.EVM_SWAP_EVENT,
] as const;

export function isSwapTypeEvent(type: HistoryEventEntryType): boolean {
  return Array.prototype.includes.call(SWAP_EVENTS, type);
}
