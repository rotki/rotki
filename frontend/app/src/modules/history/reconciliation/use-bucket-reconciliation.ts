import type { Ref } from 'vue';
import type {
  BucketStatus,
  ReconciliationAccount,
  ReconciliationBucket,
  StatusCounts,
} from '@/modules/history/reconciliation/schemas';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import {
  ACCOUNT_PAGE_SIZE,
  MAX_ACCOUNT_BUCKETS,
  useBucketReconciliationApi,
} from '@/modules/history/reconciliation/api/use-bucket-reconciliation-api';
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
const accountRequestSeq = new Map<string, number>();

function nextAccountRequest(key: string): number {
  const next = (accountRequestSeq.get(key) ?? 0) + 1;
  accountRequestSeq.set(key, next);
  return next;
}

interface UseBucketReconciliationReturn {
  accounts: Ref<ReconciliationAccount[]>;
  attention: Ref<number>;
  ensureAccount: (account: ReconciliationAccount, statuses?: BucketStatus[]) => Promise<void>;
  ensureSummary: () => Promise<void>;
  loadMore: (account: ReconciliationAccount, statuses?: BucketStatus[]) => Promise<void>;
  refreshAll: (statuses?: BucketStatus[]) => Promise<void>;
  refreshSummary: () => Promise<void>;
  reloadAccounts: (statuses?: BucketStatus[]) => Promise<void>;
  retryAccount: (account: ReconciliationAccount, statuses?: BucketStatus[]) => Promise<void>;
  summaryFailed: Ref<boolean>;
  summaryLoading: Ref<boolean>;
  totals: Ref<StatusCounts>;
}

/**
 * Fetches the reconciliation report and the rows of expanded accounts.
 *
 * @remarks
 * The store is synchronous state; all waiting happens here. Account rows are fetched lazily, once
 * per account and status filter, and are never loaded just because the summary lists the account.
 */
export function useBucketReconciliation(): UseBucketReconciliationReturn {
  const api = useBucketReconciliationApi();
  const store = useBucketReconciliationStore();
  const { attention, summaryFailed, summaryLoading, totals } = storeToRefs(store);
  const accounts = computed<ReconciliationAccount[]>(() => get(store.summary)?.accounts ?? []);

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
      store.markSummaryFailed();
    }
    finally {
      if (request === summaryRequestSeq)
        store.setSummaryLoading(false);
    }
  }

  function statusSignature(statuses?: BucketStatus[]): string {
    return statuses?.length ? [...statuses].sort().join(',') : 'all';
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

  function initialAccountState(
    current: AccountDetailState | undefined,
    options: { append?: boolean },
    statusKey: string,
  ): AccountDetailState {
    return {
      buckets: options.append ? current?.buckets ?? [] : [],
      error: undefined,
      loaded: false,
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
      error: getErrorMessage(error),
      loaded: false,
      loading: false,
    };
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
    options: { append?: boolean; force?: boolean; offset?: number } = {},
  ): Promise<void> {
    const key = accountKeyOf(account);
    const statusKey = statusSignature(statuses);
    const current = store.accountState(key);

    if (canReuseAccount(current, statusKey, options))
      return;

    const request = nextAccountRequest(key);
    const offset = options.offset ?? 0;
    const base = initialAccountState(current, options, statusKey);
    store.setAccountState(key, base);

    try {
      const response = await api.fetchAccount({
        limit: ACCOUNT_PAGE_SIZE,
        location: account.location,
        locationLabel: account.locationLabel ?? '',
        offset,
        status: statuses,
      });
      if (isLatestAccountRequest(key, request))
        store.setAccountState(key, loadedAccountState(base, response, !!options.append, offset));
    }
    catch (error: unknown) {
      if (isLatestAccountRequest(key, request) && !isRequestCancellation(error))
        store.setAccountState(key, failedAccountState(base, error));
    }
  }

  async function ensureAccount(account: ReconciliationAccount, statuses?: BucketStatus[]): Promise<void> {
    await fetchAccountRows(account, statuses);
  }

  async function retryAccount(account: ReconciliationAccount, statuses?: BucketStatus[]): Promise<void> {
    await fetchAccountRows(account, statuses, { force: true });
  }

  async function loadMore(account: ReconciliationAccount, statuses?: BucketStatus[]): Promise<void> {
    const state = store.accountState(accountKeyOf(account));
    if (!state || state.loading || state.buckets.length >= MAX_ACCOUNT_BUCKETS)
      return;

    await fetchAccountRows(account, statuses, {
      append: true,
      force: true,
      offset: state.buckets.length,
    });
  }

  async function reloadAccounts(statuses?: BucketStatus[]): Promise<void> {
    const latest = get(store.summary)?.accounts ?? [];
    const byKey = new Map(latest.map(account => [accountKeyOf(account), account]));
    const statusKey = statusSignature(statuses);
    const loadedKeys = Object.entries(get(store.accounts))
      .filter(([, state]) => state.loaded || (state.loading && state.statusKey !== statusKey))
      .map(([key]) => key);

    await Promise.all(loadedKeys.map(async (key) => {
      const account = byKey.get(key);
      if (!account) {
        store.removeAccountState(key);
        return;
      }
      await fetchAccountRows(account, statuses, { force: true });
    }));
  }

  async function refreshAll(statuses?: BucketStatus[]): Promise<void> {
    await refreshSummary();
    await reloadAccounts(statuses);
  }

  return {
    accounts,
    attention,
    ensureAccount,
    ensureSummary,
    loadMore,
    refreshAll,
    refreshSummary,
    reloadAccounts,
    retryAccount,
    summaryFailed,
    summaryLoading,
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
