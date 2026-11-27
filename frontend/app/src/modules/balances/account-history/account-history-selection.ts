import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import dayjs from 'dayjs';
import { isOfEnum } from '@/modules/core/common/helpers/is-of-enum';
import { firstQueryValue } from '@/modules/core/table/route';

export const AccountHistoryRange = {
  ALL: 'all',
  YEAR: '1y',
  HALF_YEAR: '6m',
  QUARTER: '3m',
  MONTH: '1m',
} as const;

export type AccountHistoryRange = typeof AccountHistoryRange[keyof typeof AccountHistoryRange];

const RANGE_MONTHS = {
  [AccountHistoryRange.YEAR]: 12,
  [AccountHistoryRange.HALF_YEAR]: 6,
  [AccountHistoryRange.QUARTER]: 3,
  [AccountHistoryRange.MONTH]: 1,
} as const satisfies Record<Exclude<AccountHistoryRange, 'all'>, number>;

/** The route query keys the page keeps its selection in, so a selection is a link. */
export const AccountHistoryQueryKeys = {
  ACCOUNT: 'account',
  ASSET: 'asset',
  LOCATION: 'location',
  RANGE: 'range',
} as const;

export interface AccountHistorySelection {
  /** The account's `location_label`: an address, or an exchange account's name. */
  readonly account: string | undefined;
  readonly asset: string | undefined;
  /** Narrows the account's buckets to one location; absent shows every location. */
  readonly location: string | undefined;
  readonly range: AccountHistoryRange;
}

const isRange = isOfEnum(AccountHistoryRange);

/** A query value as one non-empty string; a repeated key keeps its first value. */
function single(value: LocationQuery[string] | undefined): string | undefined {
  return firstQueryValue(value) || undefined;
}

export function parseSelection(query: LocationQuery): AccountHistorySelection {
  const range = single(query[AccountHistoryQueryKeys.RANGE]);
  return {
    account: single(query[AccountHistoryQueryKeys.ACCOUNT]),
    asset: single(query[AccountHistoryQueryKeys.ASSET]),
    location: single(query[AccountHistoryQueryKeys.LOCATION]),
    range: isRange(range) ? range : AccountHistoryRange.ALL,
  };
}

/**
 * The selection as route query entries, leaving out what is unset and the default range, so the
 * plain page URL means "nothing picked, all time".
 */
export function toSelectionQuery(selection: AccountHistorySelection): Record<string, string> {
  const query: Record<string, string> = {};
  if (selection.account)
    query[AccountHistoryQueryKeys.ACCOUNT] = selection.account;
  if (selection.asset)
    query[AccountHistoryQueryKeys.ASSET] = selection.asset;
  if (selection.location)
    query[AccountHistoryQueryKeys.LOCATION] = selection.location;
  if (selection.range !== AccountHistoryRange.ALL)
    query[AccountHistoryQueryKeys.RANGE] = selection.range;
  return query;
}

/** A link to the account history page with an account and asset already picked. */
export function accountHistoryLink(account: string, asset: string, location?: string): RouteLocationRaw {
  return {
    name: '/balances/history/',
    query: toSelectionQuery({ account, asset, location, range: AccountHistoryRange.ALL }),
  };
}

/**
 * Where a range starts, in unix seconds.
 *
 * @param range - the preset to measure back from `now`
 * @param now - unix seconds
 * @returns 0 for all time
 */
export function rangeStart(range: AccountHistoryRange, now: number): number {
  if (range === AccountHistoryRange.ALL)
    return 0;
  return dayjs.unix(now).subtract(RANGE_MONTHS[range], 'month').unix();
}
