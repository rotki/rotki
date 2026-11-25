<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { RuiAlert } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import DataIssueDetailDrawer from '@/modules/history/data-issues/components/DataIssueDetailDrawer.vue';
import DataIssueRemediationModals from '@/modules/history/data-issues/components/DataIssueRemediationModals.vue';
import DataIssuesFilterBar from '@/modules/history/data-issues/components/DataIssuesFilterBar.vue';
import DataIssuesHeaderButtons from '@/modules/history/data-issues/components/DataIssuesHeaderButtons.vue';
import DataIssuesTable from '@/modules/history/data-issues/components/DataIssuesTable.vue';
import DataIssueSummaryBar from '@/modules/history/data-issues/components/DataIssueSummaryBar.vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssuesDeepLink } from '@/modules/history/data-issues/use-data-issues-deep-link';
import { useDataIssuesPageList } from '@/modules/history/data-issues/use-data-issues-page-list';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

defineOptions({
  inheritAttrs: false,
});

const { mainPage = false } = defineProps<{
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const {
  activeStates,
  clearFilters,
  collection: state,
  confirmedActive,
  confirmedCount,
  counts,
  detect,
  detectFailure,
  detecting,
  dismissInlinePanels,
  fetchIssue,
  fields,
  hasActiveFilters,
  isAllClear,
  isEmpty,
  modelEventForm,
  modelFilters,
  modelMatchingOpen,
  modelPagination,
  modelPriceUpdate,
  modelSubModalOpen,
  onModalSaved,
  reloadAll,
  remediationBusy,
  remediationFailure,
  remediationModalOpen,
  runRemediation,
  selectConfirmed,
  selectState,
  showLoading,
  summaryFailed,
} = useDataIssuesPageList(() => mainPage);

const {
  actionFailure,
  modelActionBusy,
  modelDrawerOpen,
  modelResolveOpen,
  modelSelectedIssue,
  onDismiss,
  onReopen,
  onResolveConfirm,
  onResolveRequest,
  onRetry,
  openDetail,
  resolveFailure,
  selectedIssueFailure,
} = useDataIssueDetailActions(reloadAll, () => get(state).data);

const { clearIssueQuery, deepLinkError } = useDataIssuesDeepLink({
  drawerOpen: modelDrawerOpen,
  enabled: () => mainPage,
  fetchIssue,
  openDetail,
});

const combinedActionFailure = computed(() => get(remediationFailure) ?? get(actionFailure));
const drawerFailure = computed(() => get(remediationFailure) ?? get(selectedIssueFailure));
const drawerBusy = computed<boolean>(() => get(modelActionBusy) || get(remediationBusy));

const emptyDescription = computed<string>(() =>
  get(hasActiveFilters)
    ? t('data_issues.empty.filtered')
    : t('data_issues.empty.none'),
);

/**
 * Opens the resolve dialog against one row's issue.
 *
 * @remarks
 * A single resolve dialog serves every row and acts on whichever issue is selected, so the
 * selection has to be set before it opens.
 */
function onResolveFromRow(issue: DataIssue): void {
  set(modelSelectedIssue, issue);
  onResolveRequest();
}

/**
 * Closes the overlay and pinned copies of this list when it is shown as a page.
 *
 * @remarks
 * The dedicated page supersedes them. Leaving them open would show the user the same issues twice,
 * in two places that then have to be dismissed separately.
 */
function dismissCopiesSupersededByThisPage(): void {
  if (mainPage)
    dismissInlinePanels();
}

onMounted(async () => {
  dismissCopiesSupersededByThisPage();
  await reloadAll();
});
</script>

<template>
  <TablePageLayout
    :hide-header="!mainPage"
    :child="!mainPage"
    :title="[t('navigation_menu.history'), t('navigation_menu.history_sub.data_issues')]"
    v-bind="$attrs"
  >
    <template #buttons>
      <DataIssuesHeaderButtons
        :detecting="detecting"
        :loading="showLoading"
        @detect="detect()"
        @refresh="reloadAll()"
      />
    </template>

    <FailureStrip
      v-if="detectFailure"
      class="mb-4"
      :title="detectFailure.title"
      :failure="detectFailure.failure"
      data-testid="data-issues-detect-failure"
      @retry="detect()"
    />

    <RuiAlert
      v-if="deepLinkError"
      type="warning"
      closeable
      data-testid="data-issues-deep-link-error"
      @close="clearIssueQuery()"
    >
      {{ deepLinkError }}
    </RuiAlert>

    <NoDataScreen
      v-if="isAllClear"
      full
      variant="success"
      icon="lu-shield-check"
      data-testid="data-issues-all-clear"
    >
      <template #title>
        {{ t('data_issues.empty.all_clear_title') }}
      </template>
      {{ t('data_issues.empty.all_clear_subtitle') }}
    </NoDataScreen>

    <div
      v-else
      class="flex flex-col gap-4"
    >
      <DataIssueSummaryBar
        :counts="counts"
        :confirmed-count="confirmedCount"
        :confirmed-active="confirmedActive"
        :failed="summaryFailed"
        :active-states="activeStates"
        @select="selectState($event)"
        @select-confirmed="selectConfirmed()"
      />

      <FailureStrip
        v-if="combinedActionFailure && !modelDrawerOpen"
        :title="combinedActionFailure.title"
        :failure="combinedActionFailure.failure"
        data-testid="data-issues-action-failure"
      />

      <DataIssuesTable
        v-model:pagination="modelPagination"
        :rows="state.data"
        :loading="showLoading"
        :empty-description="emptyDescription"
        :show-clear-filters="isEmpty && hasActiveFilters"
        @open="openDetail($event)"
        @goto="router.push($event)"
        @dismiss="onDismiss($event.id)"
        @reopen="onReopen($event.id)"
        @retry="onRetry($event.id)"
        @resolve="onResolveFromRow($event)"
        @clear-filters="clearFilters()"
      >
        <template #toolbar>
          <DataIssuesFilterBar
            v-model="modelFilters"
            :fields="fields"
          />
        </template>
      </DataIssuesTable>
    </div>

    <DataIssueDetailDrawer
      v-model="modelDrawerOpen"
      :issue="modelSelectedIssue"
      :busy="drawerBusy"
      :modal-open="remediationModalOpen"
      :failure="drawerFailure"
      @dismiss="onDismiss($event)"
      @remediate="runRemediation($event)"
      @reopen="onReopen($event)"
      @retry="onRetry($event)"
      @resolve="onResolveRequest()"
    />

    <ResolveManuallyDialog
      v-model="modelResolveOpen"
      :loading="modelActionBusy"
      :failure="resolveFailure"
      @confirm="onResolveConfirm($event)"
    />

    <DataIssueRemediationModals
      v-model:price-update="modelPriceUpdate"
      v-model:event-form="modelEventForm"
      v-model:matching-open="modelMatchingOpen"
      v-model:sub-modal-open="modelSubModalOpen"
      @saved="onModalSaved()"
    />
  </TablePageLayout>
</template>
