import type {
  ReconciliationBucket,
  ReconciliationPagination,
  ReconciliationResponse,
  StatusCounts,
} from '@/modules/history/reconciliation/schemas';
import {
  attentionCount,
  EMPTY_STATUS_COUNTS,
} from '@/modules/history/reconciliation/use-reconciliation-rows';

/**
 * The rows loaded for one expanded account, and why they may be missing.
 *
 * @remarks
 * `statusKey` records the status filter the rows were fetched with. A detail fetched for the
 * Needs-attention filter must not be reused by the All-balances view, which asks a different
 * question of the same endpoint.
 */
export interface AccountDetailState {
  buckets: ReconciliationBucket[];
  pagination: ReconciliationPagination;
  statusKey: string;
  loaded: boolean;
  loading: boolean;
  /** What the last fetch threw, kept whole so the row can word it and decide on a retry. */
  error?: unknown;
}

/**
 * Shared, synchronously-updated state for the reconciliation report.
 *
 * @remarks
 * The fetching composable owns the async work. This store holds what is on screen, the previous
 * summary while a refresh runs, and the per-account rows, so the badge and the page read one
 * number rather than fetching twice.
 */
export const useBucketReconciliationStore = defineStore('history/reconciliation', () => {
  const summary = ref<ReconciliationResponse>();
  const summaryLoaded = ref<boolean>(false);
  const summaryLoading = ref<boolean>(false);
  /**
   * Why the last refresh failed, kept whole so the page can name the cause and decide on a retry.
   * The previous summary, if any, is still what is shown.
   */
  const summaryFailure = shallowRef<unknown>();
  /**
   * The backend does not serve the report, because it runs without the accounting update.
   *
   * @remarks
   * The frontend flag is fixed when the app is built and the backend flag is read when the backend
   * starts, so a build can show this page against a backend that refuses it. A retry cannot help.
   */
  const summaryUnavailable = ref<boolean>(false);
  const accounts = ref<Record<string, AccountDetailState>>({});

  const totals = computed<StatusCounts>(() => get(summary)?.totals ?? EMPTY_STATUS_COUNTS);

  const attention = computed<number>(() => attentionCount(get(totals)));

  const summaryFailed = computed<boolean>(() => get(summaryFailure) !== undefined);

  function setSummary(response: ReconciliationResponse): void {
    set(summary, response);
    set(summaryLoaded, true);
    set(summaryFailure, undefined);
    set(summaryUnavailable, false);
  }

  function setSummaryLoading(loading: boolean): void {
    set(summaryLoading, loading);
  }

  function markSummaryFailed(failure: unknown): void {
    set(summaryFailure, failure);
  }

  function markSummaryUnavailable(): void {
    set(summary, undefined);
    set(summaryUnavailable, true);
    set(accounts, {});
  }

  function accountState(key: string): AccountDetailState | undefined {
    return get(accounts)[key];
  }

  function setAccountState(key: string, state: AccountDetailState): void {
    set(accounts, { ...get(accounts), [key]: state });
  }

  function removeAccountState(key: string): void {
    const { [key]: removed, ...rest } = get(accounts);
    if (removed)
      set(accounts, rest);
  }

  function reset(): void {
    set(summary, undefined);
    set(summaryLoaded, false);
    set(summaryLoading, false);
    set(summaryFailure, undefined);
    set(summaryUnavailable, false);
    set(accounts, {});
  }

  return {
    accountState,
    accounts,
    attention,
    markSummaryFailed,
    markSummaryUnavailable,
    removeAccountState,
    reset,
    setAccountState,
    setSummary,
    setSummaryLoading,
    summary,
    summaryFailed,
    summaryFailure,
    summaryLoaded,
    summaryLoading,
    summaryUnavailable,
    totals,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBucketReconciliationStore, import.meta.hot));
