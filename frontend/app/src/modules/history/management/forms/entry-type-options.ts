import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { isChainEventKind } from '@/modules/history/management/forms/chain-event-entry-form';
import { isChainSwapKind } from '@/modules/history/management/forms/chain-swap-event-form';
import { EVM_EVENTS, isEvmTypeEvent, isSolanaTypeEvent, SOLANA_EVENTS } from '@/modules/history/management/forms/form-guards';

type EventFormData = GroupEventData | StandaloneEventData;

/**
 * The entry types an event may take: within an existing transaction, only its chain's types.
 *
 * @remarks
 * A new event is offered one swap type and one history event type, since both take their chain
 * kind from the location. An edited event shows its own type, chain kinds included.
 */
export function entryTypeOptions(data: EventFormData): HistoryEventEntryType[] {
  if (data.type === 'group-add' && isEvmTypeEvent(data.group.entryType))
    return [...EVM_EVENTS];
  if (data.type === 'group-add' && isSolanaTypeEvent(data.group.entryType))
    return [...SOLANA_EVENTS];
  const types = Object.values(HistoryEventEntryType);
  return data.type === 'add' ? types.filter(type => !isChainSwapKind(type) && !isChainEventKind(type)) : types;
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
