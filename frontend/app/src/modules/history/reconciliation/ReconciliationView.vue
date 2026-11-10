<script setup lang="ts">
import { addAccountLink } from '@/modules/accounts/add-account-link';
import DataIssuesTabs from '@/modules/history/data-issues/DataIssuesTabs.vue';
import ReconciliationHeader from '@/modules/history/reconciliation/components/ReconciliationHeader.vue';
import ReconciliationStatusBar from '@/modules/history/reconciliation/components/ReconciliationStatusBar.vue';
import ReconciliationTable from '@/modules/history/reconciliation/components/ReconciliationTable.vue';
import { totalBuckets } from '@/modules/history/reconciliation/use-reconciliation-rows';
import { useReconciliationView } from '@/modules/history/reconciliation/use-reconciliation-view';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  accounts,
  attention,
  checkError,
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
  refreshSummary,
  retryAccount,
  selectView,
  summary,
  summaryFailure,
  summaryLoading,
  summaryUnavailable,
  totals,
  view,
  visible,
} = useReconciliationView();
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.history'), t('navigation_menu.history_sub.data_issues')]"
  >
    <template #buttons>
      <DataIssuesTabs />
    </template>

    <div class="flex flex-col gap-4">
      <NoDataScreen
        v-if="summaryUnavailable"
        full
        icon="lu-scale"
        data-testid="reconciliation-unavailable"
      >
        <template #title>
          {{ t('data_issues.reconciliation.unavailable.title') }}
        </template>
        {{ t('data_issues.reconciliation.unavailable.description') }}
      </NoDataScreen>

      <div
        v-else-if="summaryLoading && !summary"
        class="rounded-rui-card border border-default p-4"
        data-testid="reconciliation-loading"
      >
        <RuiProgress
          variant="indeterminate"
          color="primary"
          data-testid="reconciliation-loading-progress"
        />
      </div>

      <FailureStrip
        v-else-if="summaryFailure !== undefined && !summary"
        :title="t('data_issues.reconciliation.failure.load')"
        :failure="summaryFailure"
        data-testid="reconciliation-summary-error"
        @retry="refreshSummary()"
      />

      <NoDataScreen
        v-else-if="hasNoAccounts"
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
        <FailureStrip
          v-if="summaryFailure !== undefined"
          :title="t('data_issues.reconciliation.failure.refresh')"
          :failure="summaryFailure"
          data-testid="reconciliation-summary-stale"
          @retry="refreshSummary()"
        />

        <div
          class="flex flex-col gap-4"
          :class="{ 'opacity-70': summary.stale || summary.processing }"
          data-testid="reconciliation-content"
        >
          <ReconciliationHeader
            :totals="totals"
            :last-compared-at="lastComparedAt"
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
              @retry="retryAccount($event)"
              @load-more="loadMore($event)"
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
                @click="selectView('all')"
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
                name="lu-eye-off"
                size="14"
              />
              <span>{{ hiddenSummary }}</span>
              <RuiButton
                size="sm"
                variant="text"
                color="primary"
                data-testid="reconciliation-show-all"
                @click="selectView('all')"
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
