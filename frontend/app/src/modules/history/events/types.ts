import type { DialogShowOptions } from '@/components/history/events/dialog-types';
import type { PullEthBlockEventPayload, PullEvmTransactionPayload } from '@/types/history/events';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';

interface HistoryEventIgnorePayload {
  readonly type: 'ignore';
  readonly event: HistoryEventEntry;
}

interface HistoryEventDeletionPayload {
  readonly type: 'delete';
  readonly ids: number[];
}

export type HistoryEventDeletePayload = HistoryEventIgnorePayload | HistoryEventDeletionPayload;

export interface HistoryEventsTableEmits {
  'show:dialog': [options: DialogShowOptions];
  'set-page': [page: number];
  'refresh': [payload?: PullEvmTransactionPayload];
  'refresh:block-event': [payload: PullEthBlockEventPayload];
  'update-event-ids': [payload: { eventIds: number[]; groupedEvents: Record<string, HistoryEventRow[]> }];
}

export type HistoryEventsTableEmitFn = <K extends keyof HistoryEventsTableEmits>(
  event: K,
  ...args: HistoryEventsTableEmits[K]
) => void;
