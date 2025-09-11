import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { isSwapTypeEvent } from '@/modules/history/management/forms/form-guards';

export interface TransactionGroup {
  chain: string;
  eventIdentifier: string;
  events: number[];
}

export interface SwapGroup {
  groupIds: number[];
  selectedIds: number[];
}

export interface AnalyzedEvents {
  completeTransactions: Map<string, TransactionGroup>;
  partialEventIds: number[];
  partialSwapGroups: SwapGroup[];
}

export function analyzeSelectedEvents(
  selectedIds: number[],
  originalGroups: HistoryEventRow[],
  groupedEventsByTxRef: Record<string, HistoryEventRow[]>,
): AnalyzedEvents {
  const selectedSet = new Set(selectedIds);
  const completeTransactions = new Map<string, TransactionGroup>();
  const partialSwapGroups: SwapGroup[] = [];
  const processedIds = new Set<number>();

  // Check each group (includes both EVM transactions and swap groups)
  originalGroups.forEach((group) => {
    if (Array.isArray(group)) {
      processArrayGroup(group, selectedSet, partialSwapGroups, processedIds);
    }
    else if (isSwapTypeEvent(group.entryType)) {
      processSingleSwapEvent(group, originalGroups, selectedSet, partialSwapGroups, processedIds);
    }
    else if (group.entryType === HistoryEventEntryType.EVM_EVENT) {
      processEvmTransaction(group, groupedEventsByTxRef, selectedSet, completeTransactions, partialSwapGroups, processedIds);
    }
  });

  // Get remaining event IDs after excluding processed events
  const partialEventIds = selectedIds.filter(id => !processedIds.has(id));

  return { completeTransactions, partialEventIds, partialSwapGroups };
}

function processArrayGroup(
  group: HistoryEventEntry[],
  selectedSet: Set<number>,
  partialSwapGroups: SwapGroup[],
  processedIds: Set<number>,
): void {
  const isSwapGroup = group.length > 0 && group.some(event => isSwapTypeEvent(event.entryType));

  if (isSwapGroup) {
    const groupEventIds = group.map(event => event.identifier);
    const selectedInGroup = groupEventIds.filter(id => selectedSet.has(id));

    if (selectedInGroup.length > 0 && selectedInGroup.length < groupEventIds.length) {
      // Partial selection - need to warn user and include all events
      partialSwapGroups.push({
        groupIds: groupEventIds,
        selectedIds: selectedInGroup,
      });
      // Mark all events as processed since we'll delete the entire group
      groupEventIds.forEach(id => processedIds.add(id));
    }
    // If all events are selected, they'll be included in partialEventIds for correct counting
  }
  else {
    // Non-swap array group - process normally
    const groupEventIds = group.map(event => event.identifier);
    const selectedInGroup = groupEventIds.filter(id => selectedSet.has(id));
    selectedInGroup.forEach(id => processedIds.add(id));
  }
}

function processSingleSwapEvent(
  group: HistoryEventEntry,
  allGroups: HistoryEventRow[],
  selectedSet: Set<number>,
  partialSwapGroups: SwapGroup[],
  processedIds: Set<number>,
): void {
  const eventIdentifier = group.eventIdentifier;
  const relatedEvents = allGroups.filter((g) => {
    if (Array.isArray(g)) {
      return g.some(e => e.eventIdentifier === eventIdentifier && isSwapTypeEvent(e.entryType));
    }
    return !Array.isArray(g) && g.eventIdentifier === eventIdentifier && isSwapTypeEvent(g.entryType);
  });

  const allSwapEventIds = relatedEvents.flatMap((g) => {
    if (Array.isArray(g)) {
      return g.filter(e => e.eventIdentifier === eventIdentifier).map(e => e.identifier);
    }
    return g.identifier;
  });

  const selectedInSwap = allSwapEventIds.filter(id => selectedSet.has(id));

  if (selectedInSwap.length > 0 && selectedInSwap.length < allSwapEventIds.length && !processedIds.has(group.identifier)) {
    // Partial selection - warn and include all
    partialSwapGroups.push({
      groupIds: allSwapEventIds,
      selectedIds: selectedInSwap,
    });
    allSwapEventIds.forEach(id => processedIds.add(id));
  }
  // If all events are selected, they'll be included in partialEventIds for correct counting
}

function processEvmTransaction(
  group: HistoryEventEntry,
  groupedEvents: Record<string, HistoryEventRow[]>,
  selectedSet: Set<number>,
  completeTransactions: Map<string, TransactionGroup>,
  partialSwapGroups: SwapGroup[],
  processedIds: Set<number>,
): void {
  const eventIdentifier = group.eventIdentifier;
  const txEvents = groupedEvents[eventIdentifier];

  if (txEvents && txEvents.length > 0) {
    // Check if this transaction contains swap events
    const hasSwapEvents = txEvents.some((event: HistoryEventRow) => {
      if (Array.isArray(event)) {
        return event.some(e => isSwapTypeEvent(e.entryType));
      }
      return isSwapTypeEvent(event.entryType);
    });

    // Get all event IDs for this transaction
    const eventIds = txEvents.flatMap((event: HistoryEventRow) =>
      Array.isArray(event) ? event.map(e => e.identifier) : event.identifier,
    );

    const selectedInTx = eventIds.filter((id: number) => selectedSet.has(id));

    if (selectedInTx.length > 0) {
      if (hasSwapEvents && selectedInTx.length < eventIds.length) {
        // Partial selection in a transaction with swap events - treat as partial swap
        partialSwapGroups.push({
          groupIds: eventIds,
          selectedIds: selectedInTx,
        });
        eventIds.forEach(id => processedIds.add(id));
      }
      else if (selectedInTx.length === eventIds.length) {
        // All events selected - treat as complete transaction
        const txRef = 'txRef' in group && group.txRef ? group.txRef : group.eventIdentifier;
        completeTransactions.set(txRef, {
          chain: group.location,
          eventIdentifier,
          events: eventIds,
        });
        eventIds.forEach(id => processedIds.add(id));
      }
    }
  }
}
