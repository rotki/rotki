<template>
  <progress-screen v-if="loading">
    {{ tc('profit_loss_report.loading') }}
  </progress-screen>
  <v-container v-else>
    <report-header :period="report" />
    <card v-if="showUpgradeMessage" class="mt-4 mb-8">
      <i18n tag="div" path="profit_loss_report.upgrade" class="text-subtitle-1">
        <template #processed>
          <span class="font-weight-medium">{{ report.entriesFound }}</span>
        </template>
        <template #start>
          <date-display
            :timestamp="report.firstProcessedTimestamp"
            class="font-weight-medium"
            no-timezone
          />
        </template>
      </i18n>
      <i18n tag="div" path="profit_loss_report.upgrade2">
        <template #link>
          <base-external-link
            :text="tc('upgrade_row.rotki_premium')"
            :href="premiumURL"
          />
        </template>
      </i18n>
    </card>
    <accounting-settings-display
      :accounting-settings="report.settings"
      class="mt-4 mb-8"
    />
    <div v-if="latest" class="d-flex">
      <export-report-csv class="mr-4" />
      <report-actionable
        :report="report"
        :initial-open="initialOpenReportActionable"
      />
    </div>
    <profit-loss-overview
      class="mt-8"
      :report="report"
      :symbol="report.settings.profitCurrency"
      :loading="loading"
    />
    <profit-loss-events
      class="mt-8"
      :report="report"
      :refreshing="refreshing"
      @update:page="onPage"
    />
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import AccountingSettingsDisplay from '@/components/profitloss/AccountingSettingsDisplay.vue';
import ExportReportCsv from '@/components/profitloss/ExportReportCsv.vue';
import ProfitLossEvents from '@/components/profitloss/ProfitLossEvents.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import ReportActionable from '@/components/profitloss/ReportActionable.vue';
import ReportHeader from '@/components/profitloss/ReportHeader.vue';
import { useRoute, useRouter } from '@/composables/common';
import { useInterop } from '@/electron-interop';
import { Routes } from '@/router/routes';
import { useReports } from '@/store/reports';

const loading = ref(true);
const refreshing = ref(false);
const reportsStore = useReports();
const { report, reports } = storeToRefs(reportsStore);

const { fetchReports, fetchReport, clearReport, isLatestReport } = reportsStore;
const { premiumURL } = useInterop();
const router = useRouter();
const route = useRoute();
let firstPage = true;

const initialOpenReportActionable = ref<boolean>(false);

const currentRoute = get(route);
const reportId = parseInt(currentRoute.params.id);
const latest = isLatestReport(reportId);

const { tc } = useI18n();

onMounted(async () => {
  if (get(reports).entries.length === 0) {
    await fetchReports();
  }
  const success = await fetchReport(reportId);
  if (!success) {
    router.push(Routes.PROFIT_LOSS_REPORTS.route);
  }

  if (get(route).query.openReportActionable) {
    set(initialOpenReportActionable, true);
    router.replace({ query: {} });
  }

  if (get(route).query.openReportActionable) {
    set(initialOpenReportActionable, true);
    router.replace({ query: {} });
  }
  set(loading, false);
});

const showUpgradeMessage = computed(
  () =>
    get(report).entriesLimit > 0 &&
    get(report).entriesLimit < get(report).entriesFound
);

onUnmounted(() => clearReport());

const onPage = async ({
  limit,
  offset,
  reportId
}: {
  reportId: number;
  limit: number;
  offset: number;
}) => {
  if (firstPage) {
    firstPage = false;
    return;
  }
  set(refreshing, true);
  await fetchReport(reportId, { limit, offset });
  set(refreshing, false);
};
</script>
