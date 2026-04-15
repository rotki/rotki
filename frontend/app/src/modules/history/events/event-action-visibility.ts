import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import {
  isGroupEditableHistoryEvent,
  isSwapTypeEvent,
} from '@/modules/history/management/forms/form-guards';
import { isAssetMovementEvent } from '@/utils/history/events';

export function hideEditAction(item: HistoryEventEntry, index: number): boolean {
  const isSwapSubEvent = isSwapTypeEvent(item.entryType) && index !== 0;
  const isAssetMovementFee = isAssetMovementEvent(item) && item.eventSubtype === 'fee';
  return isAssetMovementFee || isSwapSubEvent;
}

export function hideDeleteAction(item: HistoryEventEntry, index: number, completeGroupEvents: HistoryEventEntry[]): boolean {
  const isAssetMovementFee = isAssetMovementEvent(item) && item.eventSubtype === 'fee';
  if (isAssetMovementFee)
    return true;

  if (isSwapTypeEvent(item.entryType) && index !== 0) {
    const subtype = item.eventSubtype;
    if (subtype === 'fee')
      return false;

    const count = completeGroupEvents.filter(
      e => isSwapTypeEvent(e.entryType) && e.eventSubtype === subtype,
    ).length;

    return count <= 1;
  }

  return false;
}

export function shouldDeleteGroup(item: HistoryEventEntry, index: number): boolean {
  if (isSwapTypeEvent(item.entryType))
    return index === 0;

  return isGroupEditableHistoryEvent(item);
}
