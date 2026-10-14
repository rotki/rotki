<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { Report } from '@/modules/reports/report-types';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';
import ProfitLossOverview from '@/modules/reports/ProfitLossOverview.vue';
import { calculateTotalProfitLoss } from '@/modules/reports/report-utils';
import ReportsTableRowActions from '@/modules/reports/ReportsTableRowActions.vue';
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
  // the period names a report, so it leads; the figures follow, and when it was made comes last, quieter
  {
    cellClass: 'whitespace-nowrap',
    key: 'startTs',
    label: t('profit_loss_reports.columns.period'),
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
    cellClass: 'whitespace-nowrap',
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

const sort = ref<DataTableSortColumn<ReportData>>({
  column: 'timestamp',
  direction: 'desc',
});

useRememberTableSorting<ReportData>(TableId.REPORTS, sort, tableHeaders);
</script>

<template>
  <section class="flex flex-col gap-3">
    <h2 class="text-base font-semibold text-rui-text">
      {{ t('profit_loss_reports.title') }}
    </h2>
    <TableFrame>
      <RuiDataTable
        v-model:expanded="expanded"
        v-model:sort="sort"
        :cols="tableHeaders"
        :rows="items"
        single-expand
        row-attr="identifier"
        data-testid="reports-table"
      >
        <template
          v-if="showUpgradeMessage"
          #body.prepend
        >
          <UpgradeRow
            :total="limits.total"
            :limit="limits.limit"
            :colspan="tableHeaders.length"
            :label="t('plan_limit.labels.reports')"
          />
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay
            class="text-rui-text-secondary"
            :timestamp="row.timestamp"
          />
        </template>
        <template #item.startTs="{ row }">
          <i18n-t
            scope="global"
            keypath="profit_loss_report.report_period"
            tag="span"
            class="font-medium text-rui-text"
          >
            <template #start>
              <DateDisplay
                no-time
                :timestamp="row.startTs"
              />
            </template>
            <template #end>
              <DateDisplay
                no-time
                :timestamp="row.endTs"
              />
            </template>
          </i18n-t>
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
          <ReportsTableRowActions
            :report-id="row.identifier"
            @delete="deleteReport(row.identifier)"
          />
        </template>
        <template #expanded-item="{ row }">
          <ProfitLossOverview
            flat
            :report="row"
          />
        </template>
      </RuiDataTable>
    </TableFrame>
  </section>
</template>
