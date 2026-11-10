import type { ComputedRef, Ref } from 'vue';
import type { BucketStatus, ReconciliationAccount, ReconciliationBucket, ReconciliationResponse } from '@/modules/history/reconciliation/schemas';
import { startPromise } from '@shared/utils';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { useConfirm } from '@/modules/core/common/use-confirm';
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

interface UseReconciliationViewReturn {
  accounts: Readonly<Ref<ReconciliationAccount[]>>;
  attention: Readonly<Ref<number>>;
  checkError: Readonly<Ref<string | undefined>>;
  details: Readonly<Ref<Record<string, AccountDetailState>>>;
  detecting: Readonly<Ref<boolean>>;
  hasNoAccounts: ComputedRef<boolean>;
  hiddenBalanceCount: ComputedRef<number>;
  hiddenSummary: ComputedRef<string>;
  isNeverCompared: ComputedRef<boolean>;
  lastComparedAt: ComputedRef<number | null>;
  summary: Readonly<Ref<ReconciliationResponse | undefined>>;
  summaryFailure: Readonly<Ref<unknown>>;
  summaryLoading: Readonly<Ref<boolean>>;
  summaryUnavailable: Readonly<Ref<boolean>>;
  totals: ReturnType<typeof useBucketReconciliation>['totals'];
  view: ComputedRef<ReconciliationView>;
  visible: ComputedRef<ReconciliationAccount[]>;
  checkNow: () => Promise<void>;
  expandAccount: (account: ReconciliationAccount) => void;
  loadMore: (account: ReconciliationAccount) => void;
  markSpam: (bucket: ReconciliationBucket) => Promise<void>;
  openIssue: (issueId: number) => void;
  refreshSummary: () => Promise<void>;
  retryAccount: (account: ReconciliationAccount) => void;
  selectView: (value: string | number) => void;
}

/**
 * State and actions of the reconciliation page.
 *
 * @remarks
 * The default view is chosen once, from the first summary the page sees: it focuses on what needs
 * attention, or opens on every balance when nothing does. It is not re-derived afterwards, so a
 * check that clears the last mismatch does not switch the view under the user. An explicit
 * `?view=` always wins.
 */
export function useReconciliationView(): UseReconciliationViewReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = router.currentRoute;

  const checkError = ref<string>();
  const defaultView = ref<ReconciliationView>();

  const store = useBucketReconciliationStore();
  const { accounts: details, summary } = storeToRefs(store);

  const reconciliation = useBucketReconciliation();
  const { accounts, attention, summaryFailure, summaryLoading, summaryUnavailable, totals } = reconciliation;

  const { getAssetField } = useAssetInfoRetrieval();
  const { markAssetsAsSpam } = useSpamAsset();
  const { ask } = useConfirm();

  const queriedView = computed<ReconciliationView | undefined>(() => {
    const value = get(route).query.view;
    return value === 'all' || value === 'attention' ? value : undefined;
  });

  const view = computed<ReconciliationView>(() => get(queriedView) ?? get(defaultView) ?? 'attention');
  const statuses = computed<BucketStatus[] | undefined>(() => statusFilterFor(get(view)));
  const visible = computed<ReconciliationAccount[]>(() => visibleAccounts(get(accounts), get(view)));

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

  /** The summary first, so open accounts are asked again under the view it settles on. */
  async function refresh(): Promise<void> {
    await reconciliation.refreshSummary();
    await reconciliation.reloadAccounts(get(statuses));
  }

  const { detect, detecting } = useDataIssuesDetection(refresh);

  async function checkNow(): Promise<void> {
    set(checkError, undefined);
    const result = await detect();
    if (!result.success)
      set(checkError, result.message);
    if (result.conflict)
      await refresh();
  }

  function selectView(value: string | number): void {
    startPromise(router.replace({
      query: { ...get(route).query, view: value === 'all' ? 'all' : 'attention' },
    }));
  }

  function openIssue(issueId: number): void {
    startPromise(router.push({
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'issues' },
      query: { issue: String(issueId) },
    }));
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
    startPromise(reconciliation.ensureAccount(account, get(statuses)));
  }

  function retryAccount(account: ReconciliationAccount): void {
    startPromise(reconciliation.retryAccount(account, get(statuses)));
  }

  function loadMore(account: ReconciliationAccount): void {
    startPromise(reconciliation.loadMore(account, get(statuses)));
  }

  watchImmediate(summary, (current) => {
    if (current && get(defaultView) === undefined)
      set(defaultView, get(attention) > 0 ? 'attention' : 'all');
  });

  /** The rows answer a different filter per view, so an open account is asked again on a switch. */
  watch(view, () => {
    startPromise(reconciliation.reloadAccounts(get(statuses)));
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
    details,
    detecting,
    expandAccount,
    hasNoAccounts,
    hiddenBalanceCount,
    hiddenSummary,
    isNeverCompared,
    lastComparedAt,
    loadMore,
    markSpam,
    openIssue,
    refreshSummary: reconciliation.refreshSummary,
    retryAccount,
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
