<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import { startPromise } from '@shared/utils';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import DataIssueDetailDrawer from '@/modules/history/data-issues/components/DataIssueDetailDrawer.vue';
import DataIssuesTable from '@/modules/history/data-issues/components/DataIssuesTable.vue';
import DataIssueSummaryBar from '@/modules/history/data-issues/components/DataIssueSummaryBar.vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';
import { DEFAULT_LIST_STATES, IssueState } from '@/modules/history/data-issues/constants';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssueFields } from '@/modules/history/data-issues/use-data-issue-fields';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { type Filters, useDataIssuesFilter } from '@/modules/history/data-issues/use-data-issues-filter';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

defineOptions({
  inheritAttrs: false,
});

const { mainPage = false } = defineProps<{
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const { fetchData } = useDataIssues();
const { baselineTotal, counts, dismissInlinePanels, refreshSummary } = useDataIssuesSummary();
const { syncCompleted } = useSyncCompleted();

const filterSchema = useDataIssuesFilter();

const {
  collection: state,
  filter: filters,
  isLoading,
  pagination,
  refetch: refresh,
  setFilter: updateFilter,
} = useServerTable<DataIssue, DataIssuesRequestPayload, Filters>({
  fetch: fetchData,
  filterSchema,
  params: [{
    isDefault: true,
    to: 'request',
    values: computed<Record<string, unknown>>(() => ({ state: [...DEFAULT_LIST_STATES] })),
  }],
  urlState: routeWhen(mainPage),
});

const fields = useDataIssueFields();
const pillLabels = usePillBarLabels();

// Tracks whether the first load has finished. The all-clear screen keys off this
// (plus `hasAnyIssues`) instead of the list's transient `isLoading`, so a refresh
// on an empty inbox does not briefly flash the table between loading states.
const loadedOnce = ref<boolean>(false);

async function reloadAll(): Promise<void> {
  try {
    await Promise.all([refresh(), refreshSummary()]);
  }
  finally {
    set(loadedOnce, true);
  }
}

const {
  modelActionBusy,
  modelDrawerOpen,
  modelResolveOpen,
  modelSelectedIssue,
  onDismiss,
  onResolveConfirm,
  onResolveRequest,
  onRetry,
  openDetail,
} = useDataIssueDetailActions(reloadAll);

const activeStates = computed<string[]>(() => {
  const value = get(filters).state;
  if (Array.isArray(value))
    return value.map(state => state.toString());
  return value ? [value.toString()] : [];
});

const hasAnyIssues = computed<boolean>(() => get(baselineTotal) > 0);
const hasActiveFilters = computed<boolean>(() => Object.keys(get(filters)).length > 0);
const isEmpty = computed<boolean>(() => get(state).data.length === 0);

const emptyDescription = computed<string>(() =>
  get(hasActiveFilters)
    ? t('data_issues.empty.filtered')
    : t('data_issues.empty.none'),
);

const hasRemediatingRows = computed<boolean>(() =>
  get(state).data.some(issue => issue.state === IssueState.AUTO_REMEDIATING),
);

// Show the loading indicator immediately, but keep it up for a minimum time so a
// fetch that finishes almost instantly (or the 10s auto-remediation poll) does not
// make the spinner flicker on and straight back off.
const MIN_LOADING_MS = 500;
const showLoading = ref<boolean>(false);
const canHide = ref<boolean>(true);
const { start: startMinLoading } = useTimeoutFn(() => {
  set(canHide, true);
  if (!get(isLoading))
    set(showLoading, false);
}, MIN_LOADING_MS, { immediate: false });

watch(isLoading, (loading) => {
  if (loading) {
    set(showLoading, true);
    set(canHide, false);
    startMinLoading();
  }
  else if (get(canHide)) {
    set(showLoading, false);
  }
  // else: finished within the minimum window, so the timer clears it.
});

function selectState(issueState: IssueState): void {
  updateFilter({ ...get(filters), state: [issueState] });
}

function clearFilters(): void {
  updateFilter({});
}

async function goToEvent(route: RouteLocationRaw): Promise<void> {
  await router.push(route);
}

// Resolving reads the selected issue (the resolve dialog is shared), so a row-level
// resolve selects the issue first, then opens the dialog.
function onResolveFromRow(issue: DataIssue): void {
  set(modelSelectedIssue, issue);
  onResolveRequest();
}

const { pause, resume } = useIntervalFn(reloadAll, 10_000, { immediate: false });

watch(hasRemediatingRows, (remediating) => {
  if (remediating)
    resume();
  else
    pause();
});

// Reload when the history sync finishes so the table and its all-clear shield reflect
// the freshly detected issues without waiting for the slow poll or a manual refresh.
watch(syncCompleted, () => {
  startPromise(reloadAll());
});

onMounted(async () => {
  // The dedicated page supersedes the overlay/pinned copies of the inbox; close
  // them so the same list is not shown twice.
  if (mainPage)
    dismissInlinePanels();
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

    <NoDataScreen
      v-if="loadedOnce && !hasAnyIssues"
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
        :active-states="activeStates"
        @select="selectState($event)"
      />

      <RuiCard>
        <PillFilterBar
          v-model:matches="filters"
          class="mb-4"
          :fields="fields"
          :labels="pillLabels"
        />

        <DataIssuesTable
          v-model:pagination="pagination"
          :rows="state.data"
          :loading="showLoading"
          :empty-description="emptyDescription"
          :show-clear-filters="isEmpty && hasActiveFilters"
          @open="openDetail($event)"
          @goto="goToEvent($event)"
          @dismiss="onDismiss($event.id)"
          @retry="onRetry($event.id)"
          @resolve="onResolveFromRow($event)"
          @clear-filters="clearFilters()"
        />
      </RuiCard>
    </div>

    <DataIssueDetailDrawer
      v-model="modelDrawerOpen"
      :issue="modelSelectedIssue"
      :busy="modelActionBusy"
      @dismiss="onDismiss($event)"
      @retry="onRetry($event)"
      @resolve="onResolveRequest()"
    />

    <ResolveManuallyDialog
      v-model="modelResolveOpen"
      :loading="modelActionBusy"
      @confirm="onResolveConfirm($event)"
    />
  </TablePageLayout>
</template>
