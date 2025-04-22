import type { HistoryEventEntry } from '@/types/history/events';

interface HistoryEventIgnorePayload {
  readonly type: 'ignore';
  readonly event: HistoryEventEntry;
}

interface HistoryEventDeletionPayload {
  readonly type: 'delete';
  readonly ids: number[];
}

export type HistoryEventDeletePayload = HistoryEventIgnorePayload | HistoryEventDeletionPayload;
