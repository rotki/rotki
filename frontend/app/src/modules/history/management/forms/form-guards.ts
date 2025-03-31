import type { DependentHistoryEvent, HistoryEvent } from '@/types/history/events';
import { HistoryEventEntryType } from '@rotki/common';

export function isDependentHistoryEvent(event: HistoryEvent): event is DependentHistoryEvent {
  return event.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT
    || event.entryType === HistoryEventEntryType.SWAP_EVENT;
}
