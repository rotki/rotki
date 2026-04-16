<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import type { Report } from '@/modules/reports/report-types';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';
import ProfitLossOverview from '@/modules/reports/ProfitLossOverview.vue';
import { calculateTotalProfitLoss } from '@/modules/reports/report-utils';
import ReportsTableMoreAction from '@/modules/reports/ReportsTableMoreAction.vue';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { useReportsStore } from '@/modules/reports/use-reports-store';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

interface ReportData extends Report {
  free: BigNumber;
  taxable: BigNumber;
}

const expanded = ref<ReportData[]>([]);
const { reports } = storeToRefs(useReportsStore());
const { deleteReport, fetchReports } = useReportOperations();
const { t } = useI18n({ useScope: 'global' });

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
        <FiatDisplay
          :value="row.free"
          :currency="row.settings.profitCurrency ?? undefined"
          pnl
        />
      </template>
      <template #item.taxable="{ row }">
        <FiatDisplay
          :value="row.taxable"
          :currency="row.settings.profitCurrency ?? undefined"
          pnl
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
            :report-id="row.identifier"
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
