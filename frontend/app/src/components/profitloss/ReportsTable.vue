<script setup lang="ts">
import type { Report } from '@/types/reports';
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type BigNumber from 'bignumber.js';
import type { RouteLocationRaw } from 'vue-router';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import ReportsTableMoreAction from '@/components/profitloss/ReportsTableMoreAction.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useReportsStore } from '@/store/reports';
import { calculateTotalProfitLoss } from '@/utils/report';

interface ReportData extends Report {
  free: BigNumber;
  taxable: BigNumber;
}

const expanded = ref<ReportData[]>([]);
const reportStore = useReportsStore();
const { deleteReport, fetchReports, isLatestReport } = reportStore;
const { reports } = storeToRefs(reportStore);
const { t } = useI18n();

const items = computed<(ReportData & { id: number })[]>(() =>
  get(reports).entries.map((value, index) => ({
    ...value,
    ...calculateTotalProfitLoss(value),
    id: index,
  })),
);

const limits = computed(() => ({
  limit: get(reports).entriesLimit,
  total: get(reports).entriesFound,
}));

const tableHeaders = computed<DataTableColumn<ReportData>[]>(() => [
  {
    key: 'startTs',
    label: t('profit_loss_reports.columns.start'),
    sortable: true,
  },
  {
    key: 'endTs',
    label: t('profit_loss_reports.columns.end'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'free',
    label: t('profit_loss_reports.columns.taxfree_profit_loss'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'taxable',
    label: t('profit_loss_reports.columns.taxable_profit_loss'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'timestamp',
    label: t('profit_loss_reports.columns.created'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'actions',
    label: t('common.actions_text'),
    width: 140,
  },
]);

onBeforeMount(async () => await fetchReports());

const showUpgradeMessage = computed(
  () => get(reports).entriesLimit > 0 && get(reports).entriesLimit < get(reports).entriesFound,
);

function getReportUrl(identifier: number): RouteLocationRaw {
  return {
    name: '/reports/[id]',
    params: {
      id: identifier.toString(),
    },
  };
}

const latestReport = (reportId: number) => get(isLatestReport(reportId));

const sort = ref<DataTableSortColumn<ReportData>>({
  column: 'timestamp',
  direction: 'desc',
});

useRememberTableSorting<ReportData>(TableId.REPORTS, sort, tableHeaders);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('profit_loss_reports.title') }}
    </template>
    <RuiDataTable
      v-model:expanded="expanded"
      v-model:sort="sort"
      :cols="tableHeaders"
      :rows="items"
      single-expand
      outlined
      row-attr="identifier"
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
          :value="row.free"
          :fiat-currency="row.settings.profitCurrency"
        />
      </template>
      <template #item.taxable="{ row }">
        <AmountDisplay
          force-currency
          show-currency="symbol"
          pnl
          :value="row.taxable"
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
                  name="lu-file-text"
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
