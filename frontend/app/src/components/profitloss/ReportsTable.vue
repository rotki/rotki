<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { Routes } from '@/router/routes';
import { type Report } from '@/types/reports';
import { calculateTotalProfitLoss } from '@/utils/report';

const expanded: Ref<Report[]> = ref([]);
const reportStore = useReportsStore();
const { fetchReports, deleteReport, isLatestReport } = reportStore;
const { reports } = storeToRefs(reportStore);
const { t } = useI18n();

const items = computed(() =>
  get(reports).entries.map((value, index) => ({
    ...value,
    id: index
  }))
);

const limits = computed(() => ({
  total: get(reports).entriesFound,
  limit: get(reports).entriesLimit
}));

const tableHeaders: ComputedRef<DataTableHeader[]> = computed(() => [
  {
    text: t('profit_loss_reports.columns.start'),
    value: 'startTs'
  },
  {
    text: t('profit_loss_reports.columns.end'),
    value: 'endTs'
  },
  {
    text: t('profit_loss_reports.columns.taxfree_profit_loss'),
    value: 'free',
    align: 'end'
  },
  {
    text: t('profit_loss_reports.columns.taxable_profit_loss'),
    value: 'taxable',
    align: 'end'
  },
  {
    text: t('profit_loss_reports.columns.created'),
    value: 'timestamp',
    align: 'end'
  },
  {
    text: t('profit_loss_reports.columns.actions'),
    value: 'actions',
    align: 'end',
    width: 140,
    sortable: false
  },
  { text: '', value: 'expand', align: 'end', sortable: false }
]);

onBeforeMount(async () => await fetchReports());

const showUpgradeMessage = computed(
  () =>
    get(reports).entriesLimit > 0 &&
    get(reports).entriesLimit < get(reports).entriesFound
);

const getReportUrl = (identifier: number) => {
  const url = Routes.PROFIT_LOSS_REPORT;
  return url.replace(':id', identifier.toString());
};

const latestReport = (reportId: number) => get(isLatestReport(reportId));

const expand = (item: Report) => {
  set(expanded, get(expanded).includes(item) ? [] : [item]);
};
</script>

<template>
  <Card outlined-body>
    <template #title>
      {{ t('profit_loss_reports.title') }}
    </template>
    <DataTable
      :headers="tableHeaders"
      :items="items"
      sort-by="timestamp"
      single-expand
      :expanded.sync="expanded"
    >
      <template v-if="showUpgradeMessage" #body.prepend="{ headers }">
        <UpgradeRow
          :total="limits.total"
          :limit="limits.limit"
          :colspan="headers.length"
          :label="t('profit_loss_reports.title')"
        />
      </template>
      <template #item.timestamp="{ item }">
        <DateDisplay :timestamp="item.timestamp" />
      </template>
      <template #item.startTs="{ item }">
        <DateDisplay no-time :timestamp="item.startTs" />
      </template>
      <template #item.endTs="{ item }">
        <DateDisplay no-time :timestamp="item.endTs" />
      </template>
      <template #item.free="{ item }">
        <AmountDisplay
          force-currency
          pnl
          :value="calculateTotalProfitLoss(item).free"
          :fiat-currency="item.settings.profitCurrency"
        />
      </template>
      <template #item.taxable="{ item }">
        <AmountDisplay
          force-currency
          pnl
          :value="calculateTotalProfitLoss(item).taxable"
          :fiat-currency="item.settings.profitCurrency"
        />
      </template>
      <template #item.actions="{ item }">
        <ExportReportCsv v-if="latestReport(item.identifier)" icon />
        <VTooltip top open-delay="400">
          <template #activator="{ on, attrs }">
            <VBtn
              icon
              color="primary"
              v-bind="attrs"
              :to="getReportUrl(item.identifier)"
              v-on="on"
            >
              <VIcon small>mdi-open-in-app</VIcon>
            </VBtn>
          </template>
          <span>{{ t('reports_table.load.tooltip') }}</span>
        </VTooltip>

        <VTooltip top open-delay="400">
          <template #activator="{ on, attrs }">
            <VBtn
              icon
              color="primary"
              v-bind="attrs"
              @click="deleteReport(item.identifier)"
              v-on="on"
            >
              <VIcon small>mdi-delete</VIcon>
            </VBtn>
          </template>
          <span>{{ t('reports_table.delete.tooltip') }}</span>
        </VTooltip>
      </template>
      <template #expanded-item="{ headers, item }">
        <TableExpandContainer visible :colspan="headers.length">
          <ProfitLossOverview
            flat
            :report="item"
            :symbol="item.settings.profitCurrency"
          />
        </TableExpandContainer>
      </template>
      <template #item.expand="{ item }">
        <RowExpander
          :expanded="expanded.includes(item)"
          @click="expand(item)"
        />
      </template>
    </DataTable>
  </Card>
</template>
