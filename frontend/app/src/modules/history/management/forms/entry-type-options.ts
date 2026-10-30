import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { EVM_EVENTS, isEvmTypeEvent, isSolanaTypeEvent, SOLANA_EVENTS } from '@/modules/history/management/forms/form-guards';

type EventFormData = GroupEventData | StandaloneEventData;

/** The entry types a new event may take: within an existing transaction, only its chain's types. */
export function entryTypeOptions(data: EventFormData): HistoryEventEntryType[] {
  if (data.type === 'group-add' && isEvmTypeEvent(data.group.entryType))
    return [...EVM_EVENTS];
  if (data.type === 'group-add' && isSolanaTypeEvent(data.group.entryType))
    return [...SOLANA_EVENTS];
  return Object.values(HistoryEventEntryType);
}

/**
 * Whether the user may change the entry type.
 *
 * @remarks
 * An existing event keeps its type. Adding into an existing transaction may pick among its chain's
 * types, but only for an EVM or Solana group: any other group has a single type to add.
 */
export function canPickEntryType(data: EventFormData): boolean {
  if (data.type === 'add')
    return true;
  return data.type === 'group-add' && (isEvmTypeEvent(data.group.entryType) || isSolanaTypeEvent(data.group.entryType));
}

/** The entry type the form opens on: a new event starts as a plain history event. */
export function initialEntryType(data: EventFormData): HistoryEventEntryType {
  if (data.type === 'edit')
    return data.event.entryType;
  if (data.type === 'edit-group')
    return data.eventsInGroup[0].entryType;
  if (data.type === 'group-add')
    return data.group.entryType;
  return HistoryEventEntryType.HISTORY_EVENT;
}
