import type { ComputedRef, Ref } from 'vue';
import type {
  BucketStatus,
  InspectedBucket,
  ReconciliationAccount,
  ReconciliationBucket,
  ReconciliationResponse,
} from '@/modules/history/reconciliation/schemas';
import { startPromise } from '@shared/utils';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { useConfirm } from '@/modules/core/common/use-confirm';
import { useLocations } from '@/modules/core/common/use-locations';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';
import { useDataIssuesDetection } from '@/modules/history/data-issues/use-data-issues-detection';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';
import { type AccountDetailState, useBucketReconciliationStore } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import {
  latestComparedAt,
  neverCompared,
  notCheckedCount,
  type ReconciliationView,
  statusFilterFor,
  visibleAccounts,
} from '@/modules/history/reconciliation/use-reconciliation-rows';

const FILTER_DEBOUNCE_MS = 250;

function readQueryText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function matchesAccountQuery(
  account: ReconciliationAccount,
  needle: string,
  locationName?: string,
): boolean {
  return account.location.toLowerCase().includes(needle)
    || account.location.replaceAll('_', ' ').toLowerCase().includes(needle)
    || (locationName ?? '').toLowerCase().includes(needle)
    || (account.locationLabel ?? '').toLowerCase().includes(needle);
}

interface UseReconciliationViewReturn {
  accounts: Readonly<Ref<ReconciliationAccount[]>>;
  attention: Readonly<Ref<number>>;
  checkError: Readonly<Ref<string | undefined>>;
  details: Readonly<Ref<Record<string, AccountDetailState>>>;
  detecting: Readonly<Ref<boolean>>;
  filterFailure: Readonly<Ref<unknown>>;
  filterLoading: Readonly<Ref<boolean>>;
  hasActiveFilters: ComputedRef<boolean>;
  hasNoAccounts: ComputedRef<boolean>;
  hiddenBalanceCount: ComputedRef<number>;
  hiddenSummary: ComputedRef<string>;
  inspectedBucket: ComputedRef<InspectedBucket | undefined>;
  isNeverCompared: ComputedRef<boolean>;
  lastComparedAt: ComputedRef<number | null>;
  modelAccountFilter: Ref<string>;
  modelAssetFilter: Ref<string>;
  modelTraceOpen: Ref<boolean>;
  summary: Readonly<Ref<ReconciliationResponse | undefined>>;
  summaryFailure: Readonly<Ref<unknown>>;
  summaryLoading: Readonly<Ref<boolean>>;
  summaryUnavailable: Readonly<Ref<boolean>>;
  totals: ReturnType<typeof useBucketReconciliation>['totals'];
  view: ComputedRef<ReconciliationView>;
  visible: ComputedRef<ReconciliationAccount[]>;
  checkNow: () => Promise<void>;
  clearFilters: () => void;
  expandAccount: (account: ReconciliationAccount) => void;
  inspectTrace: (target: InspectedBucket) => void;
  loadMore: (account: ReconciliationAccount) => void;
  markSpam: (bucket: ReconciliationBucket) => Promise<void>;
  openIssue: (issueId: number) => void;
  refresh: () => Promise<void>;
  retryAccount: (account: ReconciliationAccount) => void;
  retryFilter: () => void;
  selectView: (value: string | number) => void;
}

/**
 * State and actions of the reconciliation page.
 *
 * @remarks
 * The default view is chosen once, from the first summary the page sees: it focuses on what needs
 * attention, or opens on every balance when nothing does. It is not re-derived afterwards, so a
 * check that clears the last mismatch does not switch the view under the user. An explicit
 * `?view=` always wins, and an active `?asset=` or `?account=` filter defaults to `all`.
 */
export function useReconciliationView(): UseReconciliationViewReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = router.currentRoute;

  const checkError = ref<string>();
  const defaultView = ref<ReconciliationView>();
  const filteredSummary = shallowRef<ReconciliationResponse>();
  const filteredSummaryAsset = shallowRef<string>('');
  const filterFailure = shallowRef<unknown>();
  const filterLoading = shallowRef<boolean>(false);
  const modelTraceOpen = shallowRef<boolean>(false);
  const inspectedBucket = shallowRef<InspectedBucket>();
  const modelAssetFilter = ref<string>(readQueryText(get(route).query.asset));
  const modelAccountFilter = ref<string>(readQueryText(get(route).query.account));
  let filterRequestSeq = 0;

  const store = useBucketReconciliationStore();
  const { accounts: details, summary } = storeToRefs(store);

  const reconciliation = useBucketReconciliation();
  const { accounts, attention, summaryFailure, summaryLoading, summaryUnavailable, totals } = reconciliation;
  const { getLocationData } = useLocations();
  const { getAssetField } = useAssetInfoRetrieval();
  const { markAssetsAsSpam } = useSpamAsset();
  const { ask } = useConfirm();
  const { detect, detecting } = useDataIssuesDetection(async () => refresh());

  const queriedView = computed<ReconciliationView | undefined>(() => {
    const value = get(route).query.view;
    return value === 'all' || value === 'attention' ? value : undefined;
  });

  const assetFilter = computed<string>(() => readQueryText(get(route).query.asset));
  const accountFilter = computed<string>(() => readQueryText(get(route).query.account));
  const hasActiveFilters = computed<boolean>(() => get(assetFilter).length > 0 || get(accountFilter).length > 0);

  const view = computed<ReconciliationView>(() =>
    get(queriedView) ?? (get(hasActiveFilters) ? 'all' : get(defaultView) ?? 'attention'));
  const statuses = computed<BucketStatus[] | undefined>(() => statusFilterFor(get(view)));

  const scopedAccounts = computed<ReconciliationAccount[]>(() =>
    get(assetFilter) ? (get(filteredSummary)?.accounts ?? []) : get(accounts));

  const visible = computed<ReconciliationAccount[]>(() => {
    const base = visibleAccounts(get(scopedAccounts), get(view));
    const needle = get(accountFilter).toLowerCase();
    return needle
      ? base.filter(account => matchesAccountQuery(account, needle, getLocationData(account.location)?.name))
      : base;
  });

  const lastComparedAt = computed<number | null>(() => latestComparedAt(get(accounts)));
  const isNeverCompared = computed<boolean>(() => !!get(summary) && neverCompared(get(accounts), get(totals)));
  const hasNoAccounts = computed<boolean>(() => !!get(summary) && get(accounts).length === 0);
  const hiddenBalanceCount = computed<number>(() => get(totals).reconciled + notCheckedCount(get(totals)));

  /** What the Needs-attention view leaves out: hidden balances, then accounts with nothing listed. */
  const hiddenSummary = computed<string>(() => {
    const balances = get(hiddenBalanceCount);
    const hiddenAccounts = get(accounts)
      .filter(account => account.counts.mismatch + account.counts.blocked === 0)
      .length;
    const parts = [t('data_issues.reconciliation.footer.hidden', { count: balances }, balances)];
    if (hiddenAccounts > 0)
      parts.push(t('data_issues.reconciliation.footer.accounts', { count: hiddenAccounts }, hiddenAccounts));
    return parts.join(' · ');
  });

  /**
   * Loads the asset-scoped summary without overwriting global badge totals.
   *
   * @returns `true` when this request settled as the active filter's current state (including empty
   * filter), `false` when superseded, cancelled, unavailable, or failed.
   */
  async function refreshFilteredSummary(): Promise<boolean> {
    const asset = get(assetFilter);
    const seq = ++filterRequestSeq;
    if (!asset) {
      set(filteredSummary, undefined);
      set(filteredSummaryAsset, '');
      set(filterFailure, undefined);
      set(filterLoading, false);
      return true;
    }

    if (get(filteredSummaryAsset) !== asset)
      set(filteredSummary, undefined);
    set(filterFailure, undefined);
    set(filterLoading, true);
    try {
      const result = await reconciliation.fetchFilteredSummary(asset);
      if (seq !== filterRequestSeq)
        return false;
      if (result.status === 'ok') {
        set(filteredSummary, result.response);
        set(filteredSummaryAsset, asset);
        return true;
      }
      if (result.status === 'failed')
        set(filterFailure, result.failure);
      return false;
    }
    finally {
      if (seq === filterRequestSeq)
        set(filterLoading, false);
    }
  }

  /** The summary first, so open accounts are asked again under the view and filter it settles on. */
  async function refresh(): Promise<void> {
    const [, filteredOk] = await Promise.all([reconciliation.refreshSummary(), refreshFilteredSummary()]);
    if (get(assetFilter) && !filteredOk)
      return;
    await reconciliation.reloadAccounts(get(statuses), get(assetFilter) || undefined, get(scopedAccounts));
  }

  async function retryFiltered(): Promise<void> {
    const asset = get(assetFilter);
    const applied = await refreshFilteredSummary();
    if (!applied || get(assetFilter) !== asset)
      return;
    await reconciliation.reloadAccounts(get(statuses), asset || undefined, get(scopedAccounts));
  }

  function retryFilter(): void {
    startPromise(retryFiltered());
  }

  async function checkNow(): Promise<void> {
    set(checkError, undefined);
    const result = await detect();
    if (!result.success)
      set(checkError, result.message);
    if (result.conflict)
      await refresh();
  }

  function updateQuery(patch: { account?: string; asset?: string; view?: ReconciliationView }): void {
    const nextQuery: Record<string, string> = {};
    for (const [key, value] of Object.entries(get(route).query)) {
      if (typeof value === 'string')
        nextQuery[key] = value;
    }
    if (patch.view !== undefined)
      nextQuery.view = patch.view;
    if (patch.asset !== undefined) {
      if (patch.asset.trim())
        nextQuery.asset = patch.asset.trim();
      else
        delete nextQuery.asset;
    }
    if (patch.account !== undefined) {
      if (patch.account.trim())
        nextQuery.account = patch.account.trim();
      else
        delete nextQuery.account;
    }
    startPromise(Promise.resolve(router.replace({ query: nextQuery })));
  }

  const syncFiltersToRoute = useDebounceFn(() => {
    const nextAsset = get(modelAssetFilter).trim();
    const nextAccount = get(modelAccountFilter).trim();
    if (nextAsset === get(assetFilter) && nextAccount === get(accountFilter))
      return;
    updateQuery({ account: nextAccount, asset: nextAsset });
  }, FILTER_DEBOUNCE_MS);

  function selectView(value: string | number): void {
    updateQuery({ view: value === 'all' ? 'all' : 'attention' });
  }

  function clearFilters(): void {
    set(modelAssetFilter, '');
    set(modelAccountFilter, '');
    updateQuery({ account: '', asset: '' });
  }

  function openIssue(issueId: number): void {
    startPromise(router.push({
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'issues' },
      query: { issue: String(issueId) },
    }));
  }

  function inspectTrace(target: InspectedBucket): void {
    set(inspectedBucket, target);
    set(modelTraceOpen, true);
  }

  async function markSpam(bucket: ReconciliationBucket): Promise<void> {
    const symbol = getAssetField(bucket.asset, 'symbol') || bucket.asset;
    const choice = await ask({
      message: t('data_issues.reconciliation.spam.message', { asset: symbol }),
      title: t('data_issues.reconciliation.spam.title', { asset: symbol }),
      type: 'warning',
    });
    if (choice !== 'confirm')
      return;

    const result = await markAssetsAsSpam([bucket.asset]);
    if (result.success)
      await refresh();
  }

  function expandAccount(account: ReconciliationAccount): void {
    startPromise(reconciliation.ensureAccount(account, get(statuses), get(assetFilter) || undefined));
  }

  function retryAccount(account: ReconciliationAccount): void {
    startPromise(reconciliation.retryAccount(account, get(statuses), get(assetFilter) || undefined));
  }

  function loadMore(account: ReconciliationAccount): void {
    startPromise(reconciliation.loadMore(account, get(statuses), get(assetFilter) || undefined));
  }

  watchImmediate(summary, (current) => {
    if (current && get(defaultView) === undefined)
      set(defaultView, get(attention) > 0 ? 'attention' : 'all');
  });

  watch(assetFilter, (next) => {
    if (get(modelAssetFilter).trim() !== next)
      set(modelAssetFilter, next);
  });

  watch(accountFilter, (next) => {
    if (get(modelAccountFilter).trim() !== next)
      set(modelAccountFilter, next);
  });

  watch([modelAssetFilter, modelAccountFilter], () => {
    startPromise(syncFiltersToRoute());
  });

  /**
   * Reloads open accounts once per asset/view transition.
   *
   * @remarks
   * Watching both together prevents a simultaneous `?asset=` + default-view flip from reloading
   * against an empty `scopedAccounts` before `refreshFilteredSummary` settles or firing twice.
   */
  watch([assetFilter, view], ([nextAsset, nextView], [prevAsset]) => {
    if (nextAsset !== prevAsset) {
      startPromise((async (): Promise<void> => {
        const applied = await refreshFilteredSummary();
        if (!applied || get(assetFilter) !== nextAsset || get(view) !== nextView)
          return;
        await reconciliation.reloadAccounts(get(statuses), nextAsset || undefined, get(scopedAccounts));
      })());
      return;
    }

    startPromise(reconciliation.reloadAccounts(get(statuses), nextAsset || undefined, get(scopedAccounts)));
  });

  useDataIssuesAutoReload(refresh);

  onMounted(() => {
    startPromise(refresh());
  });

  return {
    accounts,
    attention,
    checkError: readonly(checkError),
    checkNow,
    clearFilters,
    details,
    detecting,
    expandAccount,
    filterFailure: readonly(filterFailure),
    filterLoading: readonly(filterLoading),
    hasActiveFilters,
    hasNoAccounts,
    hiddenBalanceCount,
    hiddenSummary,
    inspectedBucket: computed<InspectedBucket | undefined>(() => get(inspectedBucket)),
    inspectTrace,
    isNeverCompared,
    lastComparedAt,
    loadMore,
    markSpam,
    modelAccountFilter,
    modelAssetFilter,
    modelTraceOpen,
    openIssue,
    refresh,
    retryAccount,
    retryFilter,
    selectView,
    summary,
    summaryFailure,
    summaryLoading,
    summaryUnavailable,
    totals,
    view,
    visible,
  };
}
