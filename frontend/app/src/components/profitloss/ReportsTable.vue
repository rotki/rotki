<template>
  <card outlined-body>
    <template #title>
      {{ $t('profit_loss_reports.title') }}
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
          :label="$t('profit_loss_reports.title')"
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
          :value="calculateTotalProfitLoss(item).free"
          :fiat-currency="item.settings.profitCurrency"
        />
      </template>
      <template #item.taxable="{ item }">
        <amount-display
          force-currency
          :value="calculateTotalProfitLoss(item).taxable"
          :fiat-currency="item.settings.profitCurrency"
        />
      </template>
      <template #item.sizeOnDisk="{ item }">
        {{ size(item.sizeOnDisk) }}
      </template>
      <template #item.actions="{ item }">
        <export-report-csv v-if="isLatestReport(item.identifier)" icon />
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
          <span>{{ $t('reports_table.load.tooltip') }}</span>
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
          <span>{{ $t('reports_table.delete.tooltip') }}</span>
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
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onBeforeMount,
  ref
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import DateDisplay from '@/components/display/DateDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import ExportReportCsv from '@/components/profitloss/ExportReportCsv.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import { setupStatusChecking } from '@/composables/common';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { Section } from '@/store/const';
import { useReports } from '@/store/reports';
import { size } from '@/utils/data';
import { calculateTotalProfitLoss } from '@/utils/report';

const getHeaders: () => DataTableHeader[] = () => [
  {
    text: i18n.t('profit_loss_reports.columns.start').toString(),
    value: 'startTs'
  },
  {
    text: i18n.t('profit_loss_reports.columns.end').toString(),
    value: 'endTs'
  },
  {
    text: i18n.t('profit_loss_reports.columns.taxfree_profit_loss').toString(),
    value: 'free',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_reports.columns.taxable_profit_loss').toString(),
    value: 'taxable',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_reports.columns.size').toString(),
    value: 'sizeOnDisk',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_reports.columns.created').toString(),
    value: 'timestamp',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_reports.columns.actions').toString(),
    value: 'actions',
    align: 'end',
    width: 140
  },
  { text: '', value: 'expand', align: 'end', sortable: false }
];

export default defineComponent({
  name: 'ReportsTable',
  components: {
    ExportReportCsv,
    UpgradeRow,
    RowExpander,
    ProfitLossOverview,
    DataTable,
    DateDisplay
  },
  setup() {
    const selected = ref<string[]>([]);
    const expanded = ref([]);
    const reportStore = useReports();
    const { fetchReports, fetchReport, deleteReport, isLatestReport } =
      reportStore;
    const { reports } = storeToRefs(reportStore);
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

    const refresh = async () => await fetchReports();

    onBeforeMount(async () => await fetchReports());

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const showUpgradeMessage = computed(
      () =>
        get(reports).entriesLimit > 0 &&
        get(reports).entriesLimit < get(reports).entriesFound
    );

    const getReportUrl = (identifier: number) => {
      const url = Routes.PROFIT_LOSS_REPORT.route;
      return url.replace(':id', identifier.toString());
    };

    return {
      items,
      expanded,
      limits,
      tableHeaders: getHeaders(),
      loading: shouldShowLoadingScreen(Section.REPORTS),
      refreshing: isSectionRefreshing(Section.REPORTS),
      showUpgradeMessage,
      size,
      refresh,
      selected,
      isLatestReport: (reportId: number) => get(isLatestReport(reportId)),
      getReportUrl,
      fetchReports,
      fetchReport,
      deleteReport,
      calculateTotalProfitLoss
    };
  }
});
</script>
