<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { DataIssue, DataIssuesRequestPayload } from '@/modules/history/data-issues/schemas';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import TableFilter from '@/modules/core/table/TableFilter.vue';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import DataIssueDetailDrawer from '@/modules/history/data-issues/components/DataIssueDetailDrawer.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import DataIssueSummaryBar from '@/modules/history/data-issues/components/DataIssueSummaryBar.vue';
import ResolveManuallyDialog from '@/modules/history/data-issues/components/ResolveManuallyDialog.vue';
import { IssueState, NON_TERMINAL_STATES } from '@/modules/history/data-issues/constants';
import { useDataIssueDetailActions } from '@/modules/history/data-issues/use-data-issue-detail-actions';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { type Filters, type Matcher, useDataIssuesFilter } from '@/modules/history/data-issues/use-data-issues-filter';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import NoDataScreen from '@/modules/shell/components/NoDataScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

defineOptions({
  inheritAttrs: false,
});

const { mainPage = false } = defineProps<{
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { fetchData } = useDataIssues();
const { baselineTotal, counts, refreshSummary } = useDataIssuesSummary();

const {
  fetchData: refresh,
  filters,
  isLoading,
  matchers,
  pagination,
  state,
  updateFilter,
} = usePaginationFilters<DataIssue, DataIssuesRequestPayload, Filters, Matcher>(fetchData, {
  defaultParams: computed(() => ({ state: [...NON_TERMINAL_STATES] })),
  filterSchema: useDataIssuesFilter,
  history: mainPage ? 'router' : false,
});

async function reloadAll(): Promise<void> {
  await Promise.all([refresh(), refreshSummary()]);
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

const headers = computed<DataTableColumn<DataIssue>[]>(() => [
  { key: 'kind', label: t('data_issues.headers.kind') },
  { key: 'asset', label: t('common.asset') },
  { key: 'account', label: t('common.account') },
  { key: 'createdAt', label: t('data_issues.headers.detected') },
  { key: 'state', label: t('data_issues.headers.state') },
  { class: 'w-[3rem]', key: 'actions', label: '' },
]);

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

function selectState(issueState: IssueState): void {
  updateFilter({ ...get(filters), state: [issueState] });
}

function clearFilters(): void {
  updateFilter({});
}

const { pause, resume } = useIntervalFn(reloadAll, 10_000, { immediate: false });

watch(hasRemediatingRows, (remediating) => {
  if (remediating)
    resume();
  else
    pause();
});

onMounted(async () => {
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
            :loading="isLoading"
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
      v-if="!hasAnyIssues && !isLoading"
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
        <div class="flex justify-end mb-4">
          <div class="w-full sm:max-w-[30rem]">
            <TableFilter
              v-model:matches="filters"
              :matchers="matchers"
            />
          </div>
        </div>

        <RuiDataTable
          v-model:pagination.external="pagination"
          outlined
          dense
          :cols="headers"
          :loading="isLoading"
          :rows="state.data"
          row-attr="id"
          :empty="{ description: emptyDescription }"
          data-testid="data-issues-table"
          @click:row="openDetail($event)"
        >
          <template #item.kind="{ row }">
            <DataIssueKindChip :kind="row.kind" />
          </template>
          <template #item.asset="{ row }">
            <AssetDetails
              v-if="row.asset"
              :asset="row.asset"
            />
            <span
              v-else
              class="text-rui-text-secondary"
            >
              -
            </span>
          </template>
          <template #item.account="{ row }">
            <LocationDisplay
              v-if="row.locationLabel"
              :identifier="row.locationLabel"
              :opens-details="false"
            />
            <LocationDisplay
              v-else
              :identifier="row.location"
            />
          </template>
          <template #item.createdAt="{ row }">
            <DateDisplay :timestamp="row.createdAt" />
          </template>
          <template #item.state="{ row }">
            <DataIssueStateChip :state="row.state" />
          </template>
          <template #item.actions>
            <RuiIcon
              name="lu-chevron-right"
              class="text-rui-text-secondary"
            />
          </template>

          <template
            v-if="isEmpty && hasActiveFilters"
            #empty-description
          >
            <div class="flex flex-col items-center gap-2 py-2">
              <span>{{ emptyDescription }}</span>
              <RuiButton
                size="sm"
                variant="text"
                color="primary"
                @click="clearFilters()"
              >
                {{ t('data_issues.empty.clear_filters') }}
              </RuiButton>
            </div>
          </template>
        </RuiDataTable>
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
