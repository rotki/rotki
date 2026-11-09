import type { BigNumber } from '@rotki/common';
import type {
  BucketStatus,
  ReconciliationAccount,
  ReconciliationBucket,
  StatusCounts,
} from '@/modules/history/reconciliation/schemas';

/** The four labels the page shows for the backend's five statuses. */
export type DisplayStatus = 'mismatch' | 'blocked' | 'not_checked' | 'matches';

export const EMPTY_STATUS_COUNTS: StatusCounts = {
  reconciled: 0,
  mismatch: 0,
  blocked: 0,
  pending: 0,
  notCompared: 0,
};

/** A stable key for the (location, label) pair the API groups by. */
export function reconciliationAccountKey(location: string, locationLabel: string | null): string {
  return `${location}\u0000${locationLabel ?? ''}`;
}

export function accountKeyOf(account: Pick<ReconciliationAccount, 'location' | 'locationLabel'>): string {
  return reconciliationAccountKey(account.location, account.locationLabel);
}

/** Balances that need the user: a mismatch or stopped processing. */
export function attentionCount(counts: StatusCounts): number {
  return counts.mismatch + counts.blocked;
}

/** Balances with no verdict: pending comparisons and unsupported buckets. */
export function notCheckedCount(counts: StatusCounts): number {
  return counts.pending + counts.notCompared;
}

export interface BucketAmounts {
  /** The amount the verdict was made from, or the current derived amount when no verdict exists. */
  derived: BigNumber | null;
  observed: BigNumber | null;
  /** Unix seconds. */
  observedAt: number | null;
  /** Unix seconds; null unless a saved comparison is shown. */
  comparedAt: number | null;
  /** Signed `observed - derived`; only a current mismatch has one. */
  delta: BigNumber | null;
}

export type ReconciliationView = 'attention' | 'all';

export function displayStatus(status: BucketStatus): DisplayStatus {
  switch (status) {
    case 'mismatch':
      return 'mismatch';
    case 'blocked':
      return 'blocked';
    case 'reconciled':
      return 'matches';
    case 'pending':
    case 'not_compared':
      return 'not_checked';
  }
}

/** The icon for a displayed status, so colour is never the only signal. */
export function displayStatusIcon(status: DisplayStatus): string {
  switch (status) {
    case 'mismatch':
      return 'lu-circle-x';
    case 'blocked':
      return 'lu-triangle-alert';
    case 'not_checked':
      return 'lu-circle-minus';
    case 'matches':
      return 'lu-circle-check';
  }
}

export function displayStatusColor(status: DisplayStatus): string {
  switch (status) {
    case 'mismatch':
      return 'text-rui-error';
    case 'blocked':
      return 'text-rui-warning';
    case 'not_checked':
      return 'text-rui-text-secondary';
    case 'matches':
      return 'text-rui-success';
  }
}

function statusRank(status: BucketStatus): number {
  switch (status) {
    case 'mismatch':
      return 0;
    case 'blocked':
      return 1;
    case 'pending':
    case 'not_compared':
      return 2;
    case 'reconciled':
      return 3;
  }
}

export function needsAttention(status: BucketStatus): boolean {
  return status === 'mismatch' || status === 'blocked';
}

/**
 * The statuses an account is asked for in each view.
 *
 * @remarks
 * Needs attention asks only for the two actionable statuses, which keeps a large account's first
 * expansion small. The account counts in the summary are always unfiltered, so hiding the other
 * rows here does not hide them from the headline.
 */
export function statusFilterFor(view: ReconciliationView): BucketStatus[] | undefined {
  return view === 'attention' ? ['mismatch', 'blocked'] : undefined;
}

/** Accounts the table can act on. Exchanges are summarised in a note instead. */
export function tableAccounts(accounts: ReconciliationAccount[]): ReconciliationAccount[] {
  return accounts.filter(account => !account.isExchange);
}

/**
 * The accounts the current view lists, most urgent first.
 *
 * @remarks
 * An account with nothing needing attention is absent from the Needs-attention view entirely, not
 * rendered with an empty list. Its counts still sit in the footer.
 */
/** Mismatches come before stopped processing, then accounts with nothing needing attention. */
function accountUrgency(account: ReconciliationAccount): number {
  if (account.counts.mismatch > 0)
    return 0;
  return account.counts.blocked > 0 ? 1 : 2;
}

export function visibleAccounts(accounts: ReconciliationAccount[], view: ReconciliationView): ReconciliationAccount[] {
  const rows = tableAccounts(accounts).filter(account => view === 'all'
    || account.counts.mismatch + account.counts.blocked > 0);

  return [...rows].sort((a, b) => {
    const urgency = accountUrgency(a) - accountUrgency(b);
    if (urgency !== 0)
      return urgency;

    return a.location.localeCompare(b.location)
      || (a.locationLabel ?? '').localeCompare(b.locationLabel ?? '');
  });
}

/**
 * Whether a mismatch is a holding with no events at all.
 *
 * @remarks
 * This is a presentation hint, not a diagnosis: a real token whose history was never pulled looks
 * the same. The row keeps both the spam and the history guidance available.
 */
export function isHistoryFree(bucket: ReconciliationBucket): boolean {
  const derived = bucket.check?.derivedBalance ?? bucket.derivedBalance;
  return bucket.status === 'mismatch'
    && bucket.lastEventTs === null
    && (derived === null || derived.isZero());
}

/**
 * The amounts a row shows.
 *
 * @remarks
 * A reconciled or mismatched row shows the saved check, because that is what the verdict was made
 * from. A pending row shows the current values, which explain what is being awaited. The two are
 * never mixed: a newer observation next to an older verdict would be a comparison that never ran.
 */
export function amountsFor(bucket: ReconciliationBucket): BucketAmounts {
  if ((bucket.status === 'reconciled' || bucket.status === 'mismatch') && bucket.check) {
    return {
      comparedAt: bucket.check.comparedAt,
      delta: bucket.status === 'mismatch' ? bucket.check.delta : null,
      derived: bucket.check.derivedBalance,
      observed: bucket.check.observedBalance,
      observedAt: bucket.check.observedAt,
    };
  }

  return {
    comparedAt: null,
    delta: null,
    derived: bucket.derivedBalance,
    observed: bucket.observedBalance,
    observedAt: bucket.observedAt,
  };
}

function compareBuckets(a: ReconciliationBucket, b: ReconciliationBucket): number {
  return statusRank(a.status) - statusRank(b.status)
    || (a.protocol ?? '').localeCompare(b.protocol ?? '')
    || a.asset.localeCompare(b.asset);
}

/** The parts of one account's one-line summary. */
export interface AccountSummary {
  mismatch: number;
  blocked: number;
  reconciled: number;
  notChecked: number;
  /** Balances the current view leaves out of the account's rows. */
  hidden: number;
}

/**
 * The counts an account header states.
 *
 * @remarks
 * Needs attention names only what is hidden, because listing every clean and uncheckable balance
 * under an account with one mismatch repeats the footer. All balances lists the four groups.
 */
export function accountSummaryFor(account: ReconciliationAccount, view: ReconciliationView): AccountSummary {
  const { counts } = account;
  const mismatch = counts.mismatch;
  const blocked = counts.blocked;
  const reconciled = counts.reconciled;
  const notChecked = counts.pending + counts.notCompared;

  return {
    blocked,
    hidden: view === 'attention' ? reconciled + notChecked : 0,
    mismatch,
    notChecked,
    reconciled,
  };
}

export function sortBuckets(buckets: ReconciliationBucket[]): ReconciliationBucket[] {
  return [...buckets].sort(compareBuckets);
}

/** What the page claims overall. */
export type HeadlineKind = 'mismatch' | 'blocked' | 'never' | 'matches' | 'partial' | 'nothing_checkable';

export interface Headline {
  kind: HeadlineKind;
  count: number;
}

export function totalBuckets(totals: StatusCounts): number {
  return totals.reconciled + totals.mismatch + totals.blocked + totals.pending + totals.notCompared;
}

/**
 * The headline for the current counts.
 *
 * @remarks
 * An all-clear is reserved for every bucket matching. With blocked, pending or unsupported
 * balances left, the headline says only that no mismatch was found; claiming otherwise would
 * overstate what a current-balance comparison proves.
 */
export function headlineFor(totals: StatusCounts): Headline {
  const total = totalBuckets(totals);
  const checked = totals.reconciled + totals.mismatch + totals.blocked;

  if (totals.mismatch > 0)
    return { count: totals.mismatch, kind: 'mismatch' };
  if (totals.blocked > 0)
    return { count: totals.blocked, kind: 'blocked' };
  if (total === 0)
    return { count: 0, kind: 'never' };
  if (checked === 0 && totals.notCompared === total)
    return { count: totals.notCompared, kind: 'nothing_checkable' };
  if (checked === 0)
    return { count: totals.pending, kind: 'never' };
  if (totals.pending > 0 || totals.notCompared > 0)
    return { count: totals.reconciled, kind: 'partial' };

  return { count: totals.reconciled, kind: 'matches' };
}

/**
 * The most recent comparison across the accounts that can be compared.
 *
 * @remarks
 * Exchanges are excluded: their buckets are never compared, so their timestamp would either be
 * absent or describe work that does not apply to them.
 */
export function latestComparedAt(accounts: ReconciliationAccount[]): number | null {
  return tableAccounts(accounts).reduce<number | null>((latest, account) => {
    const comparedAt = account.lastComparedAt;
    if (comparedAt === null)
      return latest;
    return latest === null ? comparedAt : Math.max(latest, comparedAt);
  }, null);
}

/** Whether nothing has ever been compared, so there is no table worth showing. */
export function neverCompared(accounts: ReconciliationAccount[], totals: StatusCounts): boolean {
  const compared = accounts.some(account => !account.isExchange && account.lastComparedAt !== null);
  return !compared && totals.pending > 0 && totals.reconciled + totals.mismatch + totals.blocked === 0;
}
