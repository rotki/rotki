import type {
  GroupEditableHistoryEvents,
  HistoryEvent,
  HistoryEventEntry,
  HistoryEventMeta,
} from '@/modules/history/events/schemas';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { isAssetMovementEvent } from '@/modules/history/event-utils';
import {
  isGroupEditableHistoryEvent,
  isSwapTypeEvent,
} from '@/modules/history/management/forms/form-guards';

/** Every entry type the {@link GroupEditableHistoryEvents} union admits. */
const GROUP_EDITABLE_ENTRY_TYPES: ReadonlySet<HistoryEventEntryType> = new Set([
  HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
  HistoryEventEntryType.SWAP_EVENT,
  HistoryEventEntryType.EVM_SWAP_EVENT,
  HistoryEventEntryType.SOLANA_SWAP_EVENT,
]);

/**
 * Whether an event is one the group form can bind.
 *
 * @remarks
 * Wider than `isGroupEditableHistoryEvent`, which omits the evm and solana swap variants even though
 * its own return type admits them. Widening that guard would change the other decisions it drives,
 * so the complete test lives here.
 */
function isGroupLeg(event: HistoryEventEntry): event is GroupEditableHistoryEvents & HistoryEventMeta {
  return GROUP_EDITABLE_ENTRY_TYPES.has(event.entryType);
}

/**
 * What the edit action hands the form for one row: the whole group, part of it, or the row alone.
 *
 * @remarks
 * A swap is edited as a whole, since the form needs every leg. An asset movement is edited with the
 * fee that follows it, when there is one. Anything else is edited on its own.
 *
 * @param item - the row the user acted on
 * @param completeGroupEvents - every event in the row's group, hidden and ignored included
 * @returns an `edit-group` target carrying the events the form should bind, or an `edit` target
 * carrying the single event
 */
export function editTargetFor(
  item: HistoryEvent,
  completeGroupEvents: HistoryEventEntry[],
): HistoryEventEditData {
  if (isSwapTypeEvent(item.entryType)) {
    return {
      eventsInGroup: completeGroupEvents.filter(isGroupLeg),
      type: 'edit-group',
    };
  }

  if (isGroupEditableHistoryEvent(item)) {
    const idx = completeGroupEvents.findIndex(event => event.identifier === item.identifier);
    const eventsInGroup: GroupEditableHistoryEvents[] = [item];
    const nextEvent = completeGroupEvents[idx + 1];
    if (nextEvent && isAssetMovementEvent(nextEvent) && nextEvent.eventSubtype === 'fee')
      eventsInGroup.push(nextEvent);

    return {
      eventsInGroup,
      type: 'edit-group',
    };
  }

  return {
    event: item,
    nextSequenceId: '',
    type: 'edit',
  };
}
