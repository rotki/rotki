import type { MatchedKeyword } from '@/modules/core/table/filtering';
import { ZeroValueFilter } from '@/modules/dashboard/snapshots';

/**
 * The keys the snapshot balances table filters on. Nothing is sent anywhere: this table holds its
 * rows, so these name a local predicate rather than a wire contract.
 */
export const SnapshotBalanceFilterKeys = {
  CATEGORY: 'category',
  SEARCH: 'search',
  SHOW_IGNORED: 'showIgnored',
  SHOW_SPAM: 'showSpam',
  ZERO_VALUE: 'zeroValue',
} as const;

type SnapshotBalanceFilterKey =
  typeof SnapshotBalanceFilterKeys[keyof typeof SnapshotBalanceFilterKeys];

export type Filters = MatchedKeyword<SnapshotBalanceFilterKey>;

/** Which kind of row the category pill narrows to. Absent = every kind. */
export const SnapshotCategories = {
  ASSET: 'asset',
  LIABILITY: 'liability',
  NFT: 'nft',
} as const;

export type SnapshotCategory = typeof SnapshotCategories[keyof typeof SnapshotCategories];

const categories: string[] = Object.values(SnapshotCategories);

/** The two zero-value departures the pill offers; `hide` is the default and so has no value. */
export const zeroValueChoices: string[] = [ZeroValueFilter.ALL, ZeroValueFilter.ONLY];

/**
 * What the bar currently narrows to, read out of the bag once so the row predicate does not have to
 * unwrap five values per row.
 *
 * Spam and ignored rows are hidden unless a pill says otherwise, and zero-value rows are hidden
 * unless one does, which is why all three read as departures from a default rather than as plain
 * values: an absent pill has to mean the same thing the unticked checkbox used to.
 */
export interface SnapshotFilterState {
  readonly category?: SnapshotCategory;
  readonly search: string;
  readonly showIgnored: boolean;
  readonly showSpam: boolean;
  readonly zeroValue: ZeroValueFilter;
}

/** The bag types every value as one-or-many; each of these fields is single-valued. */
function single(value: string | string[] | boolean | undefined): string | undefined {
  if (typeof value === 'boolean' || value === undefined)
    return undefined;
  return (Array.isArray(value) ? value[0] : value)?.toString();
}

function isCategory(value: string | undefined): value is SnapshotCategory {
  return value !== undefined && categories.includes(value);
}

function isZeroValueChoice(value: string | undefined): value is ZeroValueFilter {
  return value !== undefined && zeroValueChoices.includes(value);
}

export function readSnapshotFilters(filters: Filters): SnapshotFilterState {
  const category = single(filters[SnapshotBalanceFilterKeys.CATEGORY]);
  const zeroValue = single(filters[SnapshotBalanceFilterKeys.ZERO_VALUE]);

  return {
    category: isCategory(category) ? category : undefined,
    search: single(filters[SnapshotBalanceFilterKeys.SEARCH]) ?? '',
    showIgnored: filters[SnapshotBalanceFilterKeys.SHOW_IGNORED] === true,
    showSpam: filters[SnapshotBalanceFilterKeys.SHOW_SPAM] === true,
    zeroValue: isZeroValueChoice(zeroValue) ? zeroValue : ZeroValueFilter.HIDE,
  };
}

/** Isolates the valueless rows, which is what the summary's zero-value warning asks the table for. */
export function isolateZeroValue(filters: Filters): Filters {
  return { ...filters, [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ONLY };
}
