export const HISTORY_EVENT_ACTIONS = {
  DECODE: 'decode',
  QUERY: 'query',
} as const;

export type HistoryEventAction = typeof HISTORY_EVENT_ACTIONS[keyof typeof HISTORY_EVENT_ACTIONS];
