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
      <template #item.totalProfitLoss="{ item }">
        <amount-display
          :value="item.totalProfitLoss"
          :asset="item.profitCurrency"
        />
      </template>
      <template #item.totalTaxableProfitLoss="{ item }">
        <amount-display
          :value="item.totalTaxableProfitLoss"
          :asset="item.profitCurrency"
        />
      </template>
      <template #item.sizeOnDisk="{ item }">
        {{ size(item.sizeOnDisk) }}
      </template>
      <template #item.actions="{ item }">
        <export-report-csv v-if="canExport(item.identifier)" icon />
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
            :overview="item"
            flat
            :symbol="item.profitCurrency"
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
    text: i18n.t('profit_loss_reports.columns.total_profit_loss').toString(),
    value: 'totalProfitLoss',
    align: 'end'
  },
  {
    text: i18n
      .t('profit_loss_reports.columns.total_taxable_profit_loss')
      .toString(),
    value: 'totalTaxableProfitLoss',
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
  { text: '', value: 'expand', align: 'end', width: 48 }
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
    const { fetchReports, fetchReport, deleteReport, canExport } = reportStore;
    const { reports } = storeToRefs(reportStore);
    const items = computed(() =>
      reports.value.entries.map((value, index) => ({
        ...value,
        id: index
      }))
    );

    const limits = computed(() => ({
      total: reports.value.entriesFound,
      limit: reports.value.entriesLimit
    }));

    const refresh = async () => await fetchReports();

    onBeforeMount(async () => await fetchReports());

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const showUpgradeMessage = computed(
      () =>
        reports.value.entriesLimit > 0 &&
        reports.value.entriesLimit < reports.value.entriesFound
    );

    const getReportUrl = (identifier: number) => {
      const url = Routes.PROFIT_LOSS_REPORT;
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
      canExport: (reportId: number) => canExport(reportId).value,
      getReportUrl,
      fetchReports,
      fetchReport,
      deleteReport
    };
  }
});
</script>
