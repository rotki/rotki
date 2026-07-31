import type {
  EvmSwapEvent,
  GroupEditableHistoryEvents,
  SolanaSwapEvent,
  StandaloneEditableEvents,
} from '@/modules/history/events/schemas';

/** @public referenced only through inferred types; the export is required for declaration emit. */
export interface AddEventData {
  type: 'add';
  nextSequenceId: string;
}

export interface GroupAddEventData<I extends StandaloneEditableEvents | EvmSwapEvent | SolanaSwapEvent> {
  type: 'group-add';
  nextSequenceId: string;
  group: I;
}

/** @public referenced only through inferred types; the export is required for declaration emit. */
export interface EditStandaloneEventData<I extends StandaloneEditableEvents = StandaloneEditableEvents> {
  type: 'edit';
  event: I;
  nextSequenceId: string;
}

/** @public referenced only through inferred types; the export is required for declaration emit. */
export interface EditGroupEventData<D extends GroupEditableHistoryEvents = GroupEditableHistoryEvents> {
  type: 'edit-group';
  eventsInGroup: D[];
}

export type GroupEventData<
  D extends GroupEditableHistoryEvents = GroupEditableHistoryEvents,
> = AddEventData | EditGroupEventData<D> | (D extends EvmSwapEvent | SolanaSwapEvent ? GroupAddEventData<D> : never);

export type StandaloneEventData<
  I extends StandaloneEditableEvents = StandaloneEditableEvents,
> = AddEventData | GroupAddEventData<I> | EditStandaloneEventData<I>;

export type HistoryEventEditData = EditGroupEventData | EditStandaloneEventData;
