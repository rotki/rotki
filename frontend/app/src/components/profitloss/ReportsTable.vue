<template>
  <v-card>
    <v-card-title>
      <card-title> {{ $t('profit_loss_reports.title') }}</card-title>
    </v-card-title>
    <v-card-text>
      <v-sheet outlined rounded>
        <data-table
          :headers="headers"
          :items="entries"
          sort-by="timestamp"
          item-key="index"
        >
          <template #item.timestamp="{ item }">
            <date-display :timestamp="item.timestamp" />
          </template>
          <template #item.startTs="{ item }">
            <date-display no-time :timestamp="item.startTs" />
          </template>
          <template #item.endTs="{ item }">
            <date-display no-time :timestamp="item.endTs" />
          </template>
          <template #item.actions="{ item }">
            <v-btn
              class="profit_loss_report__load-report mr-2"
              depressed
              color="primary"
              @click="fetchReport(item.identifier)"
            >
              {{ $t('profit_loss_reports.actions.load_report') }}
            </v-btn>
            <v-btn
              class="profit_loss_report__delete-report"
              depressed
              color="primary"
              @click="deleteReport(item.identifier)"
            >
              {{ $t('profit_loss_reports.actions.delete_report') }}
            </v-btn>
          </template>
        </data-table>
      </v-sheet>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { PagedResourceParameters } from '@rotki/common';
import {
  computed,
  defineComponent,
  onBeforeMount,
  Ref,
  ref
} from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import DateDisplay from '@/components/display/DateDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { setupStatusChecking } from '@/composables/common';
import i18n from '@/i18n';
import { Section } from '@/store/const';
import { useReports } from '@/store/reports';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';
import { PagedReport } from '@/types/reports';

const getHeaders: () => DataTableHeader[] = () => [
  {
    text: i18n.t('profit_loss_reports.columns.created').toString(),
    value: 'timestamp'
  },
  {
    text: i18n.t('profit_loss_reports.columns.start').toString(),
    value: 'startTs'
  },
  {
    text: i18n.t('profit_loss_reports.columns.end').toString(),
    value: 'endTs'
  },
  {
    text: i18n.t('profit_loss_reports.columns.actions').toString(),
    value: 'actions'
  }
];

export default defineComponent({
  name: 'ReportsTable',
  components: {
    DataTable,
    CardTitle,
    DateDisplay
  },
  setup() {
    const selected: Ref<string[]> = ref([]);
    const store = useStore();

    const state: RotkehlchenState = store.state;
    const itemsPerPage = state.settings!!.itemsPerPage;

    const reportStore = useReports();
    const { fetchReports, fetchReport, deleteReport } = reportStore;
    const { reports } = storeToRefs(reportStore);

    const payload = ref<PagedResourceParameters>({
      limit: itemsPerPage,
      offset: 0,
      orderByAttribute: 'timestamp',
      ascending: false
    });

    const entries = computed(() => reports.value.entries);
    const limit = computed(() => reports.value.entriesLimit);
    const found = computed(() => reports.value.entriesFound);

    const refresh = async () => await fetchReports();
    const onPaginationUpdate = ({
      ascending,
      page,
      sortBy,
      itemsPerPage
    }: {
      page: number;
      itemsPerPage: number;
      sortBy: keyof PagedReport;
      ascending: boolean;
    }) => {
      const offset = (page - 1) * itemsPerPage;
      payload.value = {
        ...payload.value,
        orderByAttribute: sortBy,
        offset,
        limit: itemsPerPage,
        ascending
      };
      fetchReports().then();
    };

    onBeforeMount(async () => await fetchReports());

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    return {
      entries,
      limit,
      found,
      headers: getHeaders(),
      loading: shouldShowLoadingScreen(Section.REPORTS),
      refreshing: isSectionRefreshing(Section.REPORTS),
      refresh,
      selected,
      fetchReports,
      fetchReport,
      deleteReport,
      onPaginationUpdate
    };
  }
});
</script>
