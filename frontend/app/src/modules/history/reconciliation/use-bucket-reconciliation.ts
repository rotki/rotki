import type { Ref } from 'vue';
import { FailureCause } from '@/modules/core/api/failure-cause';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { failureCauseOf } from '@/modules/core/api/request-result';
import {
  ACCOUNT_PAGE_SIZE,
  MAX_ACCOUNT_BUCKETS,
  useBucketReconciliationApi,
} from '@/modules/history/reconciliation/api/use-bucket-reconciliation-api';
import {
  type BucketStatus,
  namedReconciliationFailure,
  type ReconciliationAccount,
  type ReconciliationBucket,
  type ReconciliationResponse,
  type StatusCounts,
} from '@/modules/history/reconciliation/schemas';
import {
  type AccountDetailState,
  useBucketReconciliationStore,
} from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import { accountKeyOf } from '@/modules/history/reconciliation/use-reconciliation-rows';

/**
 * Monotonic request ids per scope.
 *
 * @remarks
 * A summary refresh triggered by a completed sync can finish after one the user started, and a
 * slow first expansion can land after a retry. Only the newest request for a scope writes state;
 * an older answer is dropped instead of overwriting newer data.
 */
let summaryRequestSeq = 0;

const STATUS_KEYS = ['reconciled', 'mismatch', 'blocked', 'pending', 'notCompared'] as const satisfies readonly (keyof StatusCounts)[];
const accountRequestSeq = new Map<string, number>();

function nextAccountRequest(key: string): number {
  const next = (accountRequestSeq.get(key) ?? 0) + 1;
  accountRequestSeq.set(key, next);
  return next;
}

type FilteredSummaryResult =
  | { status: 'ok'; response: ReconciliationResponse }
  | { status: 'cancelled' }
  | { status: 'unavailable' }
  | { status: 'failed'; failure: unknown };

interface UseBucketReconciliationReturn {
  accounts: Readonly<Ref<ReconciliationAccount[]>>;
  attention: Readonly<Ref<number>>;
  ensureAccount: (account: ReconciliationAccount, statuses?: BucketStatus[], asset?: string) => Promise<void>;
  ensureSummary: () => Promise<void>;
  fetchFilteredSummary: (asset: string) => Promise<FilteredSummaryResult>;
  loadMore: (account: ReconciliationAccount, statuses?: BucketStatus[], asset?: string) => Promise<void>;
  refreshSummary: () => Promise<void>;
  reloadAccounts: (statuses?: BucketStatus[], asset?: string, sourceAccounts?: ReconciliationAccount[]) => Promise<void>;
  retryAccount: (account: ReconciliationAccount, statuses?: BucketStatus[], asset?: string) => Promise<void>;
  summaryFailed: Readonly<Ref<boolean>>;
  /** Why the last refresh failed, for a `FailureStrip` to word; undefined after a success. */
  summaryFailure: Readonly<Ref<unknown>>;
  summaryLoading: Readonly<Ref<boolean>>;
  summaryUnavailable: Readonly<Ref<boolean>>;
  totals: Readonly<Ref<StatusCounts>>;
}

/**
 * Fetches the reconciliation report and the rows of expanded accounts.
 *
 * @remarks
 * The store is synchronous state; all waiting happens here. Account rows are fetched lazily, once
 * per account and status filter, and are never loaded just because the summary lists the account.
 */
export function useBucketReconciliation(): UseBucketReconciliationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const store = useBucketReconciliationStore();
  const { attention, summaryFailed, summaryFailure, summaryLoading, summaryUnavailable, totals } = storeToRefs(store);
  const api = useBucketReconciliationApi();
  const accounts = computed<ReconciliationAccount[]>(() => get(store.summary)?.accounts ?? []);

  function namedFailure(error: unknown): unknown {
    return namedReconciliationFailure(error, t('data_issues.reconciliation.failure.unexpected_response'));
  }

  async function refreshSummary(): Promise<void> {
    const request = ++summaryRequestSeq;
    store.setSummaryLoading(true);
    try {
      const response = await api.fetchSummary();
      if (request !== summaryRequestSeq)
        return;
      store.setSummary(response);
    }
    catch (error: unknown) {
      if (request !== summaryRequestSeq || isRequestCancellation(error))
        return;
      if (failureCauseOf(error) === FailureCause.NOT_FOUND)
        store.markSummaryUnavailable();
      else
        store.markSummaryFailed(namedFailure(error));
    }
    finally {
      if (request === summaryRequestSeq)
        store.setSummaryLoading(false);
    }
  }

  async function fetchFilteredSummary(asset: string): Promise<FilteredSummaryResult> {
    try {
      return { response: await api.fetchSummary(asset), status: 'ok' };
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return { status: 'cancelled' };
      if (failureCauseOf(error) === FailureCause.NOT_FOUND) {
        store.markSummaryUnavailable();
        return { status: 'unavailable' };
      }
      return { failure: namedFailure(error), status: 'failed' };
    }
  }

  function normalizedAsset(asset?: string): string | undefined {
    const trimmed = asset?.trim();
    return trimmed && trimmed.length > 0 ? trimmed : undefined;
  }

  function statusSignature(statuses?: BucketStatus[], asset?: string): string {
    const base = statuses?.length ? [...statuses].sort().join(',') : 'all';
    const normalized = normalizedAsset(asset);
    return normalized ? `${base}\u0000${normalized.toLowerCase()}` : base;
  }

  async function ensureSummary(): Promise<void> {
    if (get(summaryLoading) || (get(store.summaryLoaded) && !get(summaryFailed)))
      return;
    await refreshSummary();
  }

  function canReuseAccount(
    current: AccountDetailState | undefined,
    statusKey: string,
    options: { append?: boolean; force?: boolean },
  ): boolean {
    if (options.force || options.append || current?.statusKey !== statusKey)
      return false;
    return current.loaded || current.loading;
  }

  function accountRequestLimit(
    current: AccountDetailState | undefined,
    statusKey: string,
    options: { append?: boolean; force?: boolean },
  ): number {
    if (!options.force || options.append || current?.statusKey !== statusKey)
      return ACCOUNT_PAGE_SIZE;
    return Math.min(MAX_ACCOUNT_BUCKETS, Math.max(ACCOUNT_PAGE_SIZE, current.buckets.length));
  }

  function initialAccountState(
    current: AccountDetailState | undefined,
    statusKey: string,
  ): AccountDetailState {
    return {
      buckets: current?.statusKey === statusKey ? current.buckets : [],
      error: undefined,
      loaded: current?.statusKey === statusKey && current.loaded,
      loading: true,
      pagination: current?.pagination ?? { limit: 0, offset: 0, total: 0 },
      statusKey,
    };
  }

  function loadedAccountState(
    detail: AccountDetailState,
    response: ReconciliationAccount | undefined,
    append: boolean,
    offset: number,
  ): AccountDetailState {
    const buckets = append
      ? dedupeBuckets([...detail.buckets, ...(response?.buckets ?? [])])
      : response?.buckets ?? [];
    return {
      ...detail,
      buckets,
      loaded: true,
      loading: false,
      pagination: response?.pagination ?? { limit: ACCOUNT_PAGE_SIZE, offset, total: buckets.length },
    };
  }

  function failedAccountState(detail: AccountDetailState, error: unknown): AccountDetailState {
    return {
      ...detail,
      error: namedFailure(error),
      loaded: false,
      loading: false,
    };
  }

  /**
   * Whether an account's fresh counts disagree with the summary on screen.
   *
   * @remarks
   * A balance query or a check can land between the summary request and the account request. The
   * header would then promise rows ("1 mismatch") that the account no longer has, so the summary is
   * asked again rather than left contradicting the rows under it.
   */
  function summaryCountsDiffer(key: string, counts: StatusCounts): boolean {
    const listed = get(accounts).find(account => accountKeyOf(account) === key);
    if (!listed)
      return false;
    return STATUS_KEYS.some(status => listed.counts[status] !== counts[status]);
  }

  function isLatestAccountRequest(key: string, request: number): boolean {
    return request === (accountRequestSeq.get(key) ?? 0);
  }

  /**
   * Fetches, or reuses, the rows of one account.
   *
   * @param account - the account to scope
   * @param statuses - the status filter, or undefined for every status
   * @param options - force a reload, append the next page, or point at its offset
   */
  async function fetchAccountRows(
    account: ReconciliationAccount,
    statuses: BucketStatus[] | undefined,
    options: { append?: boolean; asset?: string; force?: boolean; offset?: number } = {},
  ): Promise<void> {
    const key = accountKeyOf(account);
    const asset = normalizedAsset(options.asset);
    const statusKey = statusSignature(statuses, asset);
    const current = store.accountState(key);

    if (canReuseAccount(current, statusKey, options))
      return;

    const request = nextAccountRequest(key);
    const offset = options.offset ?? 0;
    const base = initialAccountState(current, statusKey);
    store.setAccountState(key, base);

    try {
      const response = await api.fetchAccount({
        asset,
        limit: accountRequestLimit(current, statusKey, options),
        location: account.location,
        locationLabel: account.locationLabel ?? '',
        offset,
        status: statuses,
      });
      if (isLatestAccountRequest(key, request))
        await applyAccountResponse(key, loadedAccountState(base, response, !!options.append, offset), response, !asset);
    }
    catch (error: unknown) {
      if (isLatestAccountRequest(key, request))
        applyAccountFailure(key, base, error);
    }
  }

  /** Shows the rows, then refreshes the summary if the account moved since it was read. */
  async function applyAccountResponse(
    key: string,
    state: AccountDetailState,
    response: ReconciliationAccount | undefined,
    checkSummaryDrift: boolean,
  ): Promise<void> {
    store.setAccountState(key, state);
    if (checkSummaryDrift && response && summaryCountsDiffer(key, response.counts))
      await refreshSummary();
  }

  /**
   * Names an account's failure on its row, or the whole report as unavailable.
   *
   * @remarks
   * A cancellation names nothing. A not-found cause means the backend runs without the accounting
   * update, which no single row can recover from.
   */
  function applyAccountFailure(key: string, base: AccountDetailState, error: unknown): void {
    if (isRequestCancellation(error))
      return;
    if (failureCauseOf(error) === FailureCause.NOT_FOUND)
      store.markSummaryUnavailable();
    else
      store.setAccountState(key, failedAccountState(base, error));
  }

  async function ensureAccount(account: ReconciliationAccount, statuses?: BucketStatus[], asset?: string): Promise<void> {
    await fetchAccountRows(account, statuses, { asset });
  }

  async function retryAccount(account: ReconciliationAccount, statuses?: BucketStatus[], asset?: string): Promise<void> {
    await fetchAccountRows(account, statuses, { asset, force: true });
  }

  async function loadMore(account: ReconciliationAccount, statuses?: BucketStatus[], asset?: string): Promise<void> {
    const state = store.accountState(accountKeyOf(account));
    if (!state || state.loading || state.buckets.length >= MAX_ACCOUNT_BUCKETS)
      return;

    await fetchAccountRows(account, statuses, {
      append: true,
      asset,
      force: true,
      offset: state.buckets.length,
    });
  }

  async function reloadAccounts(
    statuses?: BucketStatus[],
    asset?: string,
    sourceAccounts?: ReconciliationAccount[],
  ): Promise<void> {
    const latest = sourceAccounts ?? get(store.summary)?.accounts ?? [];
    const byKey = new Map(latest.map(account => [accountKeyOf(account), account]));
    const statusKey = statusSignature(statuses, asset);
    const loadedKeys = Object.entries(get(store.accounts))
      .filter(([, state]) => state.loaded || (state.loading && state.statusKey !== statusKey))
      .map(([key]) => key);

    await Promise.all(loadedKeys.map(async (key) => {
      const account = byKey.get(key);
      if (!account) {
        store.removeAccountState(key);
        return;
      }
      await fetchAccountRows(account, statuses, { asset, force: true });
    }));
  }

  return {
    accounts,
    attention,
    ensureAccount,
    ensureSummary,
    fetchFilteredSummary,
    loadMore,
    refreshSummary,
    reloadAccounts,
    retryAccount,
    summaryFailed,
    summaryFailure: readonly(summaryFailure),
    summaryLoading: readonly(summaryLoading),
    summaryUnavailable: readonly(summaryUnavailable),
    totals,
  };
}

/**
 * Drops rows already shown when a page is appended.
 *
 * @remarks
 * A new comparison can move a bucket while the next page is in flight, so the same identity can
 * come back twice. The first copy is kept, which is the one already on screen.
 */
function dedupeBuckets(buckets: ReconciliationBucket[]): ReconciliationBucket[] {
  const seen = new Set<string>();
  return buckets.filter((bucket) => {
    const key = `${bucket.protocol ?? ''}\u0000${bucket.asset}`;
    if (seen.has(key))
      return false;
    seen.add(key);
    return true;
  });
}
