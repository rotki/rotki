import type { Collection } from '@/modules/core/common/collection';
import type { HighlightType } from '@/modules/history/events/action-types';
import type { DialogShowOptions } from '@/modules/history/events/dialog-types';
import type {
  PullEthBlockEventPayload,
  PullLocationTransactionPayload,
} from '@/modules/history/events/event-payloads';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/modules/history/events/schemas';

/**
 * What the events table renders, as one unit: the paginated groups the embedding owns plus
 * everything that scopes the per-group event fetch underneath them.
 */
export interface HistoryEventsTableSource {
  /** Paginated group collection owned by the caller; its identifiers scope the event fetch. */
  groups: Collection<HistoryEventRow>;
  /** Current filter payload, reused as the base of the event fetch. */
  requestPayload: HistoryEventRequestPayload | undefined;
  /** Whether the caller is fetching groups; turning true cancels the in-flight event fetch. */
  groupLoading: boolean;
  /** Hides events whose asset is ignored, unless the user reveals them per group. */
  excludeIgnored: boolean;
  /** Restricts the event fetch to these identifiers; undefined loads the whole page. */
  identifiers?: string[];
}

/** Which rows to call out, and how. Absent when the embedding highlights nothing. */
export interface HistoryEventsTableHighlight {
  /** Group to highlight as a whole; the auto-scroll falls back to it when no ids are given. */
  groupIdentifier?: string;
  /** Individual event identifiers to highlight and scroll to. */
  identifiers?: string[];
  /** Style per target, keyed by event identifier or by `group:<groupIdentifier>`. */
  types?: Record<string, HighlightType>;
}

interface HistoryEventIgnorePayload {
  readonly type: 'ignore';
  readonly event: HistoryEventEntry;
}

interface HistoryEventDeletionPayload {
  readonly type: 'delete';
  readonly ids: number[];
}

export type HistoryEventDeletePayload = HistoryEventIgnorePayload | HistoryEventDeletionPayload;

export interface HistoryEventUnlinkPayload {
  readonly identifier: number;
}

export interface HistoryEventsTableEmits {
  'clear-filters': [];
  'show:dialog': [options: DialogShowOptions];
  'set-page': [page: number];
  'refresh': [payload?: PullLocationTransactionPayload];
  'refresh:block-event': [payload: PullEthBlockEventPayload];
  'update-event-ids': [payload: { eventIds: number[]; groupedEvents: Record<string, HistoryEventRow[]>; rawEvents?: HistoryEventRow[] }];
}

export type HistoryEventsTableEmitFn = <K extends keyof HistoryEventsTableEmits>(
  event: K,
  ...args: HistoryEventsTableEmits[K]
) => void;
