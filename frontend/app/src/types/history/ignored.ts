export enum IgnoreActionType {
  HISTORY_EVENTS = 'history_event',
}

export interface IgnorePayload {
  actionType: IgnoreActionType.HISTORY_EVENTS;
  data: string[];
}
