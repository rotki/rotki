import type { DependentHistoryEvent, IndependentHistoryEvent } from '@/types/history/events';

export interface AddEventData {
  type: 'add';
  nextSequenceId: string;
}

export interface GroupAddEventData<I extends IndependentHistoryEvent> {
  type: 'group-add';
  nextSequenceId: string;
  group: I;
}

export interface EditIndependentEventData<I extends IndependentHistoryEvent = IndependentHistoryEvent> {
  type: 'edit';
  event: I;
  nextSequenceId: string;
}

export interface EditDependentEventData<D extends DependentHistoryEvent = DependentHistoryEvent> {
  type: 'edit-group';
  eventsInGroup: D[];
}

export type DependentEventData<
  D extends DependentHistoryEvent = DependentHistoryEvent,
> = AddEventData | EditDependentEventData<D>;

export type IndependentEventData<
  I extends IndependentHistoryEvent = IndependentHistoryEvent,
> = AddEventData | GroupAddEventData<I> | EditIndependentEventData<I>;

export type HistoryEventEditData = EditDependentEventData | EditIndependentEventData;

export interface ShowMissingRuleForm {
  readonly type: 'missingRule';
  readonly data: HistoryEventEditData;
}

export interface ShowEventForm {
  readonly type: 'event';
  readonly data: DependentEventData | IndependentEventData;
}

export type ShowEventHistoryForm = ShowEventForm | ShowMissingRuleForm;
