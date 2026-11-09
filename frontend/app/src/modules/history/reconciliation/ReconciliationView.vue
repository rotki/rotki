<script setup lang="ts">
import type { BucketStatus, ReconciliationAccount, ReconciliationBucket } from '@/modules/history/reconciliation/schemas';
import { startPromise } from '@shared/utils';
import { addAccountLink } from '@/modules/accounts/add-account-link';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { useConfirm } from '@/modules/core/common/use-confirm';
import DataIssuesTabs from '@/modules/history/data-issues/DataIssuesTabs.vue';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';
import { useDataIssuesDetection } from '@/modules/history/data-issues/use-data-issues-detection';
import ReconciliationHeader from '@/modules/history/reconciliation/components/ReconciliationHeader.vue';
import ReconciliationStatusBar from '@/modules/history/reconciliation/components/ReconciliationStatusBar.vue';
import ReconciliationTable from '@/modules/history/reconciliation/components/ReconciliationTable.vue';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';
import { useBucketReconciliationStore } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';
import {
  latestComparedAt,
  neverCompared,
  notCheckedCount,
  type ReconciliationView as ReconciliationViewMode,
  statusFilterFor,
  totalBuckets,
  visibleAccounts,
} from '@/modules/history/reconciliation/use-reconciliation-rows';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = router.currentRoute;

const store = useBucketReconciliationStore();
const details = storeToRefs(store).accounts;
const {
  accounts,
  attention,
  ensureAccount,
  loadMore,
  refreshAll,
  refreshSummary,
  reloadAccounts,
  retryAccount,
  summaryFailed,
  summaryLoading,
  totals,
} = useBucketReconciliation();
const { summary } = storeToRefs(store);

const { getAssetField } = useAssetInfoRetrieval();
const { markAssetsAsSpam } = useSpamAsset();
const { ask } = useConfirm();

const checkError = ref<string>();

const queriedView = computed<ReconciliationViewMode | undefined>(() => {
  const value = get(route).query.view;
  return value === 'all' || value === 'attention' ? value : undefined;
});

/**
 * The open view.
 *
 * @remarks
 * An explicit `?view=` always wins, so a link or a reload keeps the view the user chose. Without
 * one the page focuses on what needs attention, and opens on every balance only when nothing does.
 */
const view = computed<ReconciliationViewMode>(() =>
  get(queriedView) ?? (get(attention) > 0 ? 'attention' : 'all'));

const statuses = computed<BucketStatus[] | undefined>(() => statusFilterFor(get(view)));
const visible = computed<ReconciliationAccount[]>(() => visibleAccounts(get(accounts), get(view)));

const lastComparedAt = computed<number | null>(() => latestComparedAt(get(accounts)));
const hasEverCompared = computed<boolean>(() => get(lastComparedAt) !== null);
const isNeverCompared = computed<boolean>(() => !!get(summary) && neverCompared(get(accounts), get(totals)));
const hasNoAccounts = computed<boolean>(() => !!get(summary) && get(accounts).length === 0);

const hiddenBalanceCount = computed<number>(() =>
  get(totals).reconciled + notCheckedCount(get(totals)));

const hiddenAccountCount = computed<number>(() =>
  get(accounts)
    .filter(account => account.counts.mismatch + account.counts.blocked === 0)
    .length);

const { detect, detecting } = useDataIssuesDetection(() => refreshAll(get(statuses)));

async function checkNow(): Promise<void> {
  set(checkError, undefined);
  const result = await detect();
  if (!result.success)
    set(checkError, result.message);
  if (result.conflict) {
    await refreshAll(get(statuses));
  }
}

function selectView(value: string | number): void {
  const next: ReconciliationViewMode = value === 'all' ? 'all' : 'attention';
  startPromise(router.replace({
    query: {
      ...get(route).query,
      view: next,
    },
  }));
}

function showAllBalances(): void {
  selectView('all');
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
    title: t('data_issues.reconciliation.spam.title'),
    type: 'warning',
  });
  if (choice !== 'confirm')
    return;

  const result = await markAssetsAsSpam([bucket.asset]);
  if (result.success)
    await refreshAll(get(statuses));
}

function expandAccount(account: Parameters<typeof ensureAccount>[0]): void {
  startPromise(ensureAccount(account, get(statuses)));
}

function retry(account: Parameters<typeof retryAccount>[0]): void {
  startPromise(retryAccount(account, get(statuses)));
}

function more(account: Parameters<typeof loadMore>[0]): void {
  startPromise(loadMore(account, get(statuses)));
}

useDataIssuesAutoReload(() => refreshAll(get(statuses)));

/** The rows answer a different filter per view, so an open account is asked again on a switch. */
watch(view, () => {
  startPromise(reloadAccounts(get(statuses)));
});

onMounted(() => {
  startPromise(refreshAll(get(statuses)));
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.history'), t('navigation_menu.history_sub.data_issues')]"
  >
    <template #buttons>
      <DataIssuesTabs />
    </template>

    <div class="flex flex-col gap-4">
      <div
        v-if="summaryLoading && !summary"
        class="rounded-rui-card border border-default p-4"
        data-testid="reconciliation-loading"
      >
        <RuiProgress
          variant="indeterminate"
          color="primary"
          data-testid="reconciliation-loading-progress"
        />
      </div>

      <RuiAlert
        v-else-if="summaryFailed && !summary"
        type="error"
        data-testid="reconciliation-summary-error"
      >
        <div class="flex items-center gap-3">
          <span>{{ t('data_issues.reconciliation.load_error') }}</span>
          <RuiButton
            size="sm"
            variant="text"
            color="primary"
            @click="refreshSummary()"
          >
            {{ t('common.actions.retry') }}
          </RuiButton>
        </div>
      </RuiAlert>

      <NoDataScreen
        v-if="hasNoAccounts"
        full
        icon="lu-wallet"
        data-testid="reconciliation-no-accounts"
      >
        <template #title>
          {{ t('data_issues.reconciliation.empty.no_accounts_title') }}
        </template>
        <div class="flex flex-col items-center gap-4">
          <span>{{ t('data_issues.reconciliation.empty.no_accounts') }}</span>
          <RouterLink :to="addAccountLink({ addresses: [] })">
            <RuiButton
              color="primary"
              data-testid="reconciliation-add-account"
            >
              <template #prepend>
                <RuiIcon name="lu-plus" />
              </template>
              {{ t('data_issues.reconciliation.empty.add_account') }}
            </RuiButton>
          </RouterLink>
        </div>
      </NoDataScreen>

      <template v-else-if="summary">
        <RuiAlert
          v-if="summaryFailed"
          type="warning"
          data-testid="reconciliation-summary-stale"
        >
          <div class="flex items-center gap-3">
            <span>{{ t('data_issues.reconciliation.load_error_stale') }}</span>
            <RuiButton
              size="sm"
              variant="text"
              color="primary"
              @click="refreshSummary()"
            >
              {{ t('common.actions.retry') }}
            </RuiButton>
          </div>
        </RuiAlert>

        <div
          class="flex flex-col gap-4"
          :class="{ 'opacity-70': summary.stale || summary.processing }"
          data-testid="reconciliation-content"
        >
          <ReconciliationHeader
            :totals="totals"
            :last-compared-at="hasEverCompared ? lastComparedAt : null"
            :detecting="detecting"
            :disabled="summary.stale || summary.processing"
            :stale="summary.stale"
            :processing="summary.processing"
            :check-error="checkError"
            @check="checkNow()"
          />

          <ReconciliationStatusBar
            v-if="totalBuckets(totals) > 0"
            :totals="totals"
          />

          <div class="flex flex-wrap items-center gap-2">
            <RuiTabs
              variant="segmented"
              :model-value="view"
              data-testid="reconciliation-view-switch"
              @update:model-value="selectView($event)"
            >
              <RuiTab value="attention">
                {{ t('data_issues.reconciliation.view.attention', { count: attention }, attention) }}
              </RuiTab>
              <RuiTab value="all">
                {{ t('data_issues.reconciliation.view.all', { count: totalBuckets(totals) }, totalBuckets(totals)) }}
              </RuiTab>
            </RuiTabs>
          </div>

          <NoDataScreen
            v-if="isNeverCompared"
            icon="lu-scale"
            data-testid="reconciliation-never-checked"
          >
            <template #title>
              {{ t('data_issues.reconciliation.headline.never') }}
            </template>
            {{ t('data_issues.reconciliation.empty.never_checked') }}
          </NoDataScreen>

          <template v-else-if="accounts.length > 0">
            <ReconciliationTable
              :accounts="visible"
              :details="details"
              :view="view"
              :loading="summaryLoading"
              @expand="expandAccount($event)"
              @retry="retry($event)"
              @load-more="more($event)"
              @open-issue="openIssue($event)"
              @mark-spam="markSpam($event)"
            />

            <div
              v-if="view === 'attention' && visible.length === 0"
              class="flex flex-wrap items-center gap-3 text-sm"
              data-testid="reconciliation-nothing-attention"
            >
              <RuiIcon
                name="lu-circle-check"
                size="16"
                class="text-rui-success"
              />
              <span>{{ t('data_issues.reconciliation.empty.nothing_attention') }}</span>
              <RuiButton
                size="sm"
                variant="text"
                color="primary"
                data-testid="reconciliation-show-all-empty"
                @click="showAllBalances()"
              >
                {{ t('data_issues.reconciliation.view.show_all') }}
              </RuiButton>
            </div>

            <div
              v-else-if="view === 'attention' && hiddenBalanceCount > 0"
              class="flex flex-wrap items-center gap-2 text-sm text-rui-text-secondary border-t border-default pt-3"
              data-testid="reconciliation-hidden-footer"
            >
              <RuiIcon
                name="lu-circle-check"
                size="14"
                class="text-rui-success"
              />
              <span>{{ t('data_issues.reconciliation.footer.hidden', { count: hiddenBalanceCount }, hiddenBalanceCount) }}</span>
              <span v-if="hiddenAccountCount > 0">
                {{ t('data_issues.reconciliation.footer.accounts', { count: hiddenAccountCount }, hiddenAccountCount) }}
              </span>
              <RuiButton
                size="sm"
                variant="text"
                color="primary"
                data-testid="reconciliation-show-all"
                @click="showAllBalances()"
              >
                {{ t('data_issues.reconciliation.view.show_all') }}
              </RuiButton>
            </div>
          </template>
        </div>
      </template>
    </div>
  </TablePageLayout>
</template>
