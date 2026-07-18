import type { ActionStatus } from '@/modules/core/common/action';
import type { HistoryEventCollectionRow, HistoryEventEntry } from '@/modules/history/events/schemas';

/**
 * The minimal shape shared by every "unmatched group of events" the matching
 * dialogs operate on: an exchange asset movement or a cross-chain bridge leg.
 */
export interface UnmatchedEventGroup {
  groupIdentifier: string;
  events: HistoryEventCollectionRow;
  asset: string;
}

/** Suggested counterpart events for an unmatched group, best matches first. */
export interface MatchSuggestions {
  closeMatches: number[];
  otherEvents: number[];
}

export interface PotentialMatchRow {
  identifier: number;
  entry: HistoryEventEntry;
  isCloseMatch: boolean;
}

/**
 * Strategy object that parametrizes the shared potential-matches UI
 * (`PotentialMatchesContent`/`PotentialMatchesList`) per matching flow, so the
 * same components serve both exchange asset movements and bridge transactions.
 */
export interface MatchingFlow {
  getSuggestions: (
    groupIdentifier: string,
    timeRangeSeconds: number,
    onlyExpectedAssets: boolean,
    tolerance: string,
  ) => Promise<MatchSuggestions>;
  match: (identifier: number, matchedEventIds: number[]) => Promise<ActionStatus>;
  refresh: (skipIgnored?: boolean) => Promise<void>;
}
