<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { RuiAlert, RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import DataIssueDetailDrawer from '@/modules/history/data-issues/components/DataIssueDetailDrawer.vue';
import DataIssuesTable from '@/modules/history/data-issues/components/DataIssuesTable.vue';
import DataIssueSummaryBar from '@/modules/history/data-issues/components/DataIssueSummaryBar.vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';
import DataIssuesTabs from '@/modules/history/data-issues/DataIssuesTabs.vue';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { useDataIssuesDetection } from '@/modules/history/data-issues/use-data-issues-detection';
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
const currentRoute = router.currentRoute;

const { fetchIssue } = useDataIssues();

const {
  activeStates,
  clearFilters,
  collection: state,
  counts,
  dismissInlinePanels,
  fields,
  hasActiveFilters,
  isAllClear,
  isEmpty,
  modelFilters: filters,
  modelPagination: pagination,
  reloadAll,
  selectState,
  showLoading,
  summaryFailed,
} = useDataIssuesPageList(() => mainPage);

const pillLabels = usePillBarLabels();

const {
  actionFailure,
  modelActionBusy,
  modelDrawerOpen,
  modelResolveOpen,
  modelSelectedIssue,
  onDismiss,
  onResolveConfirm,
  onResolveRequest,
  onRetry,
  openDetail,
  resolveFailure,
  selectedIssueFailure,
} = useDataIssueDetailActions(reloadAll, () => get(state).data);

const { detect, detectFailure, detecting } = useDataIssuesDetection(reloadAll);

/** A dead `?issue=` link is reported inline instead of as a toast about the whole inbox. */
const deepLinkError = ref<string>();
const deepLinkIssueId = ref<number>();

async function clearIssueQuery(): Promise<void> {
  if (get(currentRoute).query.issue === undefined)
    return;

  const { issue: _issue, ...query } = get(currentRoute).query;
  set(deepLinkError, undefined);
  set(deepLinkIssueId, undefined);
  await router.replace({ query });
}

async function openIssueFromQuery(): Promise<void> {
  if (!mainPage)
    return;

  const raw = get(currentRoute).query.issue;
  if (raw === undefined) {
    set(deepLinkError, undefined);
    set(deepLinkIssueId, undefined);
    return;
  }

  const id = typeof raw === 'string' ? Number(raw) : Number.NaN;
  if (!Number.isInteger(id) || id <= 0) {
    set(deepLinkError, t('data_issues.deep_link.invalid', { id: String(raw) }));
    return;
  }

  if (id === get(deepLinkIssueId))
    return;

  set(deepLinkIssueId, id);
  set(deepLinkError, undefined);

  const result = await fetchIssue(id);
  if (id !== get(deepLinkIssueId))
    return;

  if (result.issue) {
    openDetail(result.issue);
    return;
  }

  set(deepLinkError, t('data_issues.deep_link.missing', {
    error: result.error ?? '',
    id,
  }));
}

/**
 * The drawer fetches the issue itself, so a filter that excludes it does not matter. Removing the
 * query when the drawer closes keeps a later reload from reopening a link the user has dismissed.
 */
watch(() => get(currentRoute).query.issue, openIssueFromQuery, { immediate: true });

watch(modelDrawerOpen, async (open) => {
  if (!open)
    await clearIssueQuery();
});

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
      <DataIssuesTabs />
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="detecting"
            data-testid="data-issues-detect"
            @click="detect()"
          >
            <template #prepend>
              <RuiIcon name="lu-scale" />
            </template>
            {{ t('data_issues.detect.action') }}
          </RuiButton>
        </template>
        {{ t('data_issues.detect.tooltip') }}
      </RuiTooltip>

      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="showLoading"
            data-testid="data-issues-refresh"
            @click="reloadAll()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('data_issues.refresh_tooltip') }}
      </RuiTooltip>
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
        :failed="summaryFailed"
        :active-states="activeStates"
        @select="selectState($event)"
      />

      <FailureStrip
        v-if="actionFailure && !modelDrawerOpen"
        :title="actionFailure.title"
        :failure="actionFailure.failure"
        data-testid="data-issues-action-failure"
      />

      <DataIssuesTable
        v-model:pagination="pagination"
        :rows="state.data"
        :loading="showLoading"
        :empty-description="emptyDescription"
        :show-clear-filters="isEmpty && hasActiveFilters"
        @open="openDetail($event)"
        @goto="router.push($event)"
        @dismiss="onDismiss($event.id)"
        @retry="onRetry($event.id)"
        @resolve="onResolveFromRow($event)"
        @clear-filters="clearFilters()"
      >
        <template #toolbar>
          <PillFilterBar
            v-model:matches="filters"
            class="flex-1 min-w-64"
            :fields="fields"
            :labels="pillLabels"
          />
        </template>
      </DataIssuesTable>
    </div>

    <DataIssueDetailDrawer
      v-model="modelDrawerOpen"
      :issue="modelSelectedIssue"
      :busy="modelActionBusy"
      :failure="selectedIssueFailure"
      @dismiss="onDismiss($event)"
      @retry="onRetry($event)"
      @resolve="onResolveRequest()"
    />

    <ResolveManuallyDialog
      v-model="modelResolveOpen"
      :loading="modelActionBusy"
      :failure="resolveFailure"
      @confirm="onResolveConfirm($event)"
    />
  </TablePageLayout>
</template>
