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
  /**
   * Identifier of the event the matching endpoints act on. Groups that hold more
   * than the matchable event itself (an EVM transaction group also carries the gas
   * fee event) must set this, otherwise the first event of the group is used.
   */
  identifier?: number;
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
  /**
   * Search window the dialog pre-fills, in seconds. Falls back to the asset movement
   * setting when the flow does not carry its own.
   */
  defaultTimeRangeSeconds?: number;
  /** Amount tolerance the dialog pre-fills, as a decimal fraction (0.01 is 1%). */
  defaultTolerance?: string;
}
