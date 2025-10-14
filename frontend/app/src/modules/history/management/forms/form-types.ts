import type {
  EvmSwapEvent,
  GroupEditableHistoryEvents,
  SolanaSwapEvent,
  StandaloneEditableEvents,
} from '@/types/history/events/schemas';

export interface AddEventData {
  type: 'add';
  nextSequenceId: string;
}

export interface GroupAddEventData<I extends StandaloneEditableEvents | EvmSwapEvent | SolanaSwapEvent> {
  type: 'group-add';
  nextSequenceId: string;
  group: I;
}

export interface EditStandaloneEventData<I extends StandaloneEditableEvents = StandaloneEditableEvents> {
  type: 'edit';
  event: I;
  nextSequenceId: string;
}

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

export interface ShowMissingRuleForm {
  readonly type: 'missingRule';
  readonly data: HistoryEventEditData;
}

export type ShowFormData = GroupEventData | StandaloneEventData;

export interface ShowEventForm {
  readonly type: 'event';
  readonly data: ShowFormData;
}

export type ShowEventHistoryForm = ShowEventForm | ShowMissingRuleForm;
