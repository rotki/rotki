import type {
  EvmSwapEvent,
  GroupEditableHistoryEvents,
  HistoryEvent,
} from '@/types/history/events';
import { HistoryEventEntryType } from '@rotki/common';

export function isGroupEditableHistoryEvent(event: HistoryEvent): event is GroupEditableHistoryEvents {
  return event.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT
    || event.entryType === HistoryEventEntryType.SWAP_EVENT;
}

export function isEvmSwapEvent(event: HistoryEvent): event is EvmSwapEvent {
  return event.entryType === HistoryEventEntryType.EVM_SWAP_EVENT;
}
