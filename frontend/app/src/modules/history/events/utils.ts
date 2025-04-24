import type { HistoryEventEntry } from '@/types/history/events';
import { HistoryEventEntryType } from '@rotki/common';

interface SwapGroup {
  type: 'swap';
  events: HistoryEventEntry[];
}

interface SingleEvent {
  type: 'evm';
  event: HistoryEventEntry;
}

type HistoryEventGroup = SwapGroup | SingleEvent;

export function isSwap(event: HistoryEventEntry): boolean {
  return event.entryType === HistoryEventEntryType.SWAP_EVENT || event.entryType === HistoryEventEntryType.EVM_SWAP_EVENT;
}

export function groupSwaps(events: HistoryEventEntry[]): HistoryEventGroup[] {
  const grouped: HistoryEventGroup[] = [];
  let group: HistoryEventEntry[] = [];
  for (const event of events) {
    if (group.length > 0 && (!isSwap(event) || event.eventSubtype === 'spend')) {
      grouped.push({ events: group, type: 'swap' });
      group = [];
    }
    if (isSwap(event)) {
      group.push(event);
    }
    else {
      grouped.push({ event, type: 'evm' });
    }
  }
  if (group.length > 0) {
    grouped.push({ events: group, type: 'swap' });
  }
  return grouped;
}
