<template>
  <progress-screen v-if="loading">
    {{ $t('profit_loss_report.loading') }}
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
            :text="$t('upgrade_row.rotki_premium')"
            :href="$interop.premiumURL"
          />
        </template>
      </i18n>
    </card>
    <accounting-settings-display
      :accounting-settings="report.settings"
      class="mt-4"
    />
    <export-report-csv v-if="exportable" />
    <profit-loss-overview
      class="mt-8"
      :overview="report.overview"
      :symbol="report.currency"
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

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  onUnmounted,
  ref
} from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import AccountingSettingsDisplay from '@/components/profitloss/AccountingSettingsDisplay.vue';
import ExportReportCsv from '@/components/profitloss/ExportReportCsv.vue';
import ProfitLossEvents from '@/components/profitloss/ProfitLossEvents.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import ReportHeader from '@/components/profitloss/ReportHeader.vue';
import { useRoute, useRouter } from '@/composables/common';
import { Routes } from '@/router/routes';
import { useReports } from '@/store/reports';

export default defineComponent({
  name: 'ProfitLossReports',
  components: {
    ExportReportCsv,
    ProgressScreen,
    ReportHeader,
    BaseExternalLink,
    ProfitLossOverview,
    ProfitLossEvents,
    AccountingSettingsDisplay
  },
  setup() {
    const loading = ref(true);
    const refreshing = ref(false);
    const reportsStore = useReports();
    const { report, reports } = storeToRefs(reportsStore);
    const { fetchReports, fetchReport, clearReport, canExport } = reportsStore;
    const router = useRouter();
    const route = useRoute();
    let firstPage = true;

    const currentRoute = route.value;
    const reportId = parseInt(currentRoute.params.id);
    const exportable = canExport(reportId);

    onMounted(async () => {
      if (reports.value.entries.length === 0) {
        await fetchReports();
      }
      const success = await fetchReport(reportId);
      if (!success) {
        router.push(Routes.PROFIT_LOSS_REPORTS);
      }
      loading.value = false;
    });

    const showUpgradeMessage = computed(
      () =>
        report.value.entriesLimit > 0 &&
        report.value.entriesLimit < report.value.entriesFound
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
      refreshing.value = true;
      await fetchReport(reportId, { limit, offset });
      refreshing.value = false;
    };

    return {
      loading,
      refreshing,
      report,
      showUpgradeMessage,
      exportable,
      onPage
    };
  }
});
</script>
