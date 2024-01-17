<script setup lang="ts">
import { Routes } from '@/router/routes';
import { calculateTotalProfitLoss } from '@/utils/report';
import type { ComputedRef, Ref } from 'vue';
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library-compat';
import type { Report } from '@/types/reports';

const expanded: Ref<Report[]> = ref([]);
const reportStore = useReportsStore();
const { fetchReports, deleteReport, isLatestReport } = reportStore;
const { reports } = storeToRefs(reportStore);
const { t } = useI18n();

const items = computed(() =>
  get(reports).entries.map((value, index) => ({
    ...value,
    id: index,
  })),
);

const limits = computed(() => ({
  total: get(reports).entriesFound,
  limit: get(reports).entriesLimit,
}));

const tableHeaders: ComputedRef<DataTableColumn[]> = computed(() => [
  {
    label: t('profit_loss_reports.columns.start'),
    key: 'startTs',
  },
  {
    label: t('profit_loss_reports.columns.end'),
    key: 'endTs',
  },
  {
    label: t('profit_loss_reports.columns.taxfree_profit_loss'),
    key: 'free',
    align: 'end',
  },
  {
    label: t('profit_loss_reports.columns.taxable_profit_loss'),
    key: 'taxable',
    align: 'end',
  },
  {
    label: t('profit_loss_reports.columns.created'),
    key: 'timestamp',
    align: 'end',
  },
  {
    label: t('common.actions_text'),
    key: 'actions',
    align: 'end',
    width: 140,
  },
]);

onBeforeMount(async () => await fetchReports());

const showUpgradeMessage = computed(
  () =>
    get(reports).entriesLimit > 0
    && get(reports).entriesLimit < get(reports).entriesFound,
);

function getReportUrl(identifier: number) {
  const url = Routes.PROFIT_LOSS_REPORT;
  return url.replace(':id', identifier.toString());
}

const latestReport = (reportId: number) => get(isLatestReport(reportId));

const sort = ref<DataTableSortColumn>({
  column: 'timestamp',
  direction: 'desc',
});
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('profit_loss_reports.title') }}
    </template>
    <RuiDataTable
      :cols="tableHeaders"
      :rows="items"
      single-expand
      :sort="sort"
      :expanded.sync="expanded"
      outlined
      row-attr="id"
    >
      <template
        v-if="showUpgradeMessage"
        #body.prepend
      >
        <UpgradeRow
          :total="limits.total"
          :limit="limits.limit"
          :colspan="tableHeaders.length"
          :label="t('profit_loss_reports.title')"
        />
      </template>
      <template #item.timestamp="{ row }">
        <DateDisplay :timestamp="row.timestamp" />
      </template>
      <template #item.startTs="{ row }">
        <DateDisplay
          no-time
          :timestamp="row.startTs"
        />
      </template>
      <template #item.endTs="{ row }">
        <DateDisplay
          no-time
          :timestamp="row.endTs"
        />
      </template>
      <template #item.free="{ row }">
        <AmountDisplay
          force-currency
          show-currency="symbol"
          pnl
          :value="calculateTotalProfitLoss(row).free"
          :fiat-currency="row.settings.profitCurrency"
        />
      </template>
      <template #item.taxable="{ row }">
        <AmountDisplay
          force-currency
          show-currency="symbol"
          pnl
          :value="calculateTotalProfitLoss(row).taxable"
          :fiat-currency="row.settings.profitCurrency"
        />
      </template>
      <template #item.actions="{ row }">
        <div class="flex items-center justify-end gap-4">
          <RouterLink :to="getReportUrl(row.identifier)">
            <RuiButton
              size="sm"
              variant="text"
              color="primary"
            >
              <template #prepend>
                <RuiIcon
                  size="20"
                  name="file-text-line"
                />
              </template>
              {{ t('reports_table.load') }}
            </RuiButton>
          </RouterLink>

          <ReportsTableMoreAction
            :show-export-button="latestReport(row.identifier)"
            @delete="deleteReport(row.identifier)"
          />
        </div>
      </template>
      <template #expanded-item="{ row }">
        <ProfitLossOverview
          :report="row"
          :symbol="row.settings.profitCurrency"
        />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
