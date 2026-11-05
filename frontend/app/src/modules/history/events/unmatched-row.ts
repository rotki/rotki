import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { UnmatchedActionPayload, UnmatchedFailure, UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';

/** The two kinds of unmatched row a panel lists, each with its own wording. */
export const UnmatchedVariant = {
  ASSET_MOVEMENT: 'asset-movement',
  BRIDGE: 'bridge',
} as const;

export type UnmatchedVariant = typeof UnmatchedVariant[keyof typeof UnmatchedVariant];

/**
 * One unmatched row, with everything either presentation needs already decided.
 *
 * @remarks
 * The wording lives on the row rather than in a helper each presentation calls, because a helper
 * is only shared until someone forgets: the dialog table rendered the raw `deposit`/`withdrawal`
 * for a while precisely because the card had its own label function.
 */
export interface UnmatchedRow<TItem> {
  /** What the selection stores: a bridge leg's own event, or a movement's whole group. */
  id: string;
  groupIdentifier: string;
  entry: HistoryEventEntry;
  location: string;
  timestamp: number;
  original: TItem;
  typeLabel: string;
  /** The other side is not one of the user's accounts, so no match can exist. */
  untracked: boolean;
  /** Names the untracked side: the destination, or for a bridge withdrawal the source. */
  untrackedLabel: string;
  untrackedTooltip: string;
  /** Where the funds went, shown under an untracked row when known. */
  untrackedAddress?: string;
  isFiat?: boolean;
  /** Set only when the row was already resolved as a payment or as income, rather than merely ignored. */
  resolvedLabel?: string;
}

/** What the table and the cards both take: the same rows, shown as a dialog table or as pinned cards. */
export interface UnmatchedPresentationProps<TRow extends UnmatchedRow<unknown>> {
  rows: TRow[];
  specFor: (row: TRow) => UnmatchedRowActionSpec;
  emptyDescription: string;
  /** Why the last load failed, shown in place of the empty text or above the rows it left. */
  failure?: UnmatchedFailure;
  highlightedGroupIdentifier?: string;
  ignoreLoading?: boolean;
  loading?: boolean;
}

/** The table also names its location column, which reads as the exchange for asset movements. */
export interface UnmatchedTableProps<TRow extends UnmatchedRow<unknown>> extends UnmatchedPresentationProps<TRow> {
  variant: UnmatchedVariant;
}

export interface UnmatchedPresentationEmits<TItem> {
  action: [payload: UnmatchedActionPayload<TItem>];
  retry: [];
}
