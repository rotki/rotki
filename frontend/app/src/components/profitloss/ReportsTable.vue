<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { type DataTableHeader } from 'vuetify';
import { Routes } from '@/router/routes';
import { type Report } from '@/types/reports';
import { calculateTotalProfitLoss } from '@/utils/report';

const expanded: Ref<Report[]> = ref([]);
const reportStore = useReportsStore();
const { fetchReports, deleteReport, isLatestReport } = reportStore;
const { reports } = storeToRefs(reportStore);
const { tc } = useI18n();

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
    text: tc('profit_loss_reports.columns.start'),
    value: 'startTs'
  },
  {
    text: tc('profit_loss_reports.columns.end'),
    value: 'endTs'
  },
  {
    text: tc('profit_loss_reports.columns.taxfree_profit_loss'),
    value: 'free',
    align: 'end'
  },
  {
    text: tc('profit_loss_reports.columns.taxable_profit_loss'),
    value: 'taxable',
    align: 'end'
  },
  {
    text: tc('profit_loss_reports.columns.created'),
    value: 'timestamp',
    align: 'end'
  },
  {
    text: tc('profit_loss_reports.columns.actions'),
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
  <card outlined-body>
    <template #title>
      {{ tc('profit_loss_reports.title') }}
    </template>
    <data-table
      :headers="tableHeaders"
      :items="items"
      sort-by="timestamp"
      single-expand
      :expanded.sync="expanded"
    >
      <template v-if="showUpgradeMessage" #body.prepend="{ headers }">
        <upgrade-row
          :total="limits.total"
          :limit="limits.limit"
          :colspan="headers.length"
          :label="tc('profit_loss_reports.title')"
        />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.startTs="{ item }">
        <date-display no-time :timestamp="item.startTs" />
      </template>
      <template #item.endTs="{ item }">
        <date-display no-time :timestamp="item.endTs" />
      </template>
      <template #item.free="{ item }">
        <amount-display
          force-currency
          pnl
          :value="calculateTotalProfitLoss(item).free"
          :fiat-currency="item.settings.profitCurrency"
        />
      </template>
      <template #item.taxable="{ item }">
        <amount-display
          force-currency
          pnl
          :value="calculateTotalProfitLoss(item).taxable"
          :fiat-currency="item.settings.profitCurrency"
        />
      </template>
      <template #item.actions="{ item }">
        <export-report-csv v-if="latestReport(item.identifier)" icon />
        <v-tooltip top open-delay="400">
          <template #activator="{ on, attrs }">
            <v-btn
              icon
              color="primary"
              v-bind="attrs"
              :to="getReportUrl(item.identifier)"
              v-on="on"
            >
              <v-icon small>mdi-open-in-app</v-icon>
            </v-btn>
          </template>
          <span>{{ tc('reports_table.load.tooltip') }}</span>
        </v-tooltip>

        <v-tooltip top open-delay="400">
          <template #activator="{ on, attrs }">
            <v-btn
              icon
              color="primary"
              v-bind="attrs"
              @click="deleteReport(item.identifier)"
              v-on="on"
            >
              <v-icon small>mdi-delete</v-icon>
            </v-btn>
          </template>
          <span>{{ tc('reports_table.delete.tooltip') }}</span>
        </v-tooltip>
      </template>
      <template #expanded-item="{ headers, item }">
        <table-expand-container visible :colspan="headers.length">
          <profit-loss-overview
            flat
            :report="item"
            :symbol="item.settings.profitCurrency"
          />
        </table-expand-container>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          :expanded="expanded.includes(item)"
          @click="expand(item)"
        />
      </template>
    </data-table>
  </card>
</template>
