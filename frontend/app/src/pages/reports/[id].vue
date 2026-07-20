<script setup lang="ts">
import type { Report } from '@/modules/reports/report-types';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import AccountingSettingsDisplay from '@/modules/reports/AccountingSettingsDisplay.vue';
import ExportReportCsv from '@/modules/reports/ExportReportCsv.vue';
import ProfitLossEvents from '@/modules/reports/ProfitLossEvents.vue';
import ProfitLossOverview from '@/modules/reports/ProfitLossOverview.vue';
import ReportActionable from '@/modules/reports/ReportActionable.vue';
import ReportHeader from '@/modules/reports/ReportHeader.vue';
import { useReportOperations } from '@/modules/reports/use-report-operations';
import { defaultReportEvents, useReportsStore } from '@/modules/reports/use-reports-store';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';

definePage({
  meta: {
    // label-only: gives the notes sidebar a title; not shown in the drawer or search.
    nav: { labelKey: msg.$t('navigation_menu.profit_loss_report'), icon: 'lu-calculator', searchable: false },
    canNavigateBack: true,
    noteLocation: NoteLocation.PROFIT_LOSS_REPORTS,
  },
});

defineOptions({
  name: 'ReportDetail',
});

const { t } = useI18n({ useScope: 'global' });

const loading = ref(true);
const refreshing = ref(false);
const initialOpenReportActionable = ref<boolean>(false);

const reportsStore = useReportsStore();
const { actionableItems, reports } = storeToRefs(reportsStore);
const { isLatestReport } = reportsStore;
const { fetchReports, getActionableItems } = useReportOperations();

const router = useRouter();
const route = useRoute<'/reports/[id]'>();
const currentRoute = get(route);
const reportId = Number(String(currentRoute.params.id));
const latest = isLatestReport(reportId);

const selectedReport = computed<Report>(() => get(reports).entries.find(item => item.identifier === reportId)!);
const settings = computed(() => get(selectedReport).settings);

const missingAcquisitionsCount = computed<number>(() => get(actionableItems)?.missingAcquisitions.length ?? 0);
const missingPricesCount = computed<number>(() => get(actionableItems)?.missingPrices.length ?? 0);
const eventsSkippedCount = computed<number>(() => get(actionableItems)?.eventsSkippedNoRule ?? 0);
const hasActionableIssues = computed<boolean>(() => get(latest) && (get(missingAcquisitionsCount) > 0 || get(missingPricesCount) > 0));
const showCompletenessWarning = computed<boolean>(() => get(hasActionableIssues) || (get(latest) && get(eventsSkippedCount) > 0));

// Detailed issues are only kept for the latest report. For older reports we can
// still tell whether they had incomplete processing, and only then is it worth
// explaining why the details are unavailable.
const reportHadIssues = computed<boolean>(() => {
  const report = get(reports).entries.find(item => item.identifier === reportId);
  return !!report && report.processedActions < report.totalActions;
});
const showStaleDetails = computed<boolean>(() => !get(latest) && get(reportHadIssues));

const reportEvents = ref(defaultReportEvents());

onMounted(async () => {
  set(loading, true);
  if (get(reports).entries.length === 0)
    await fetchReports();

  if (get(latest)) {
    await getActionableItems();
  }

  if (get(route).query.openReportActionable) {
    set(initialOpenReportActionable, true);
    await router.replace({ query: {} });
  }

  set(loading, false);
});

async function regenerateReport() {
  const { endTs, startTs } = get(selectedReport);
  await router.push({
    path: '/reports',
    query: {
      end: endTs.toString(),
      regenerate: 'true',
      start: startTs.toString(),
    },
  });
}
</script>

<template>
  <ProgressScreen v-if="loading">
    {{ t('profit_loss_report.loading') }}
  </ProgressScreen>

  <div
    v-else
    class="container"
  >
    <div class="flex flex-col gap-8">
      <ReportHeader :period="{ start: selectedReport.startTs, end: selectedReport.endTs }" />
      <AccountingSettingsDisplay :accounting-settings="settings" />
      <div class="flex gap-2">
        <ExportReportCsv :report-id="reportId" />
        <ReportActionable
          v-if="latest"
          :report="selectedReport"
          :initial-open="initialOpenReportActionable"
          @regenerate="regenerateReport()"
        />
        <RuiButton
          color="primary"
          variant="outlined"
          @click="regenerateReport()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-refresh-ccw"
              size="18"
            />
          </template>
          {{ t('profit_loss_report.actionable.actions.regenerate_report') }}
        </RuiButton>
      </div>
      <RuiAlert
        v-if="showCompletenessWarning"
        type="warning"
      >
        <div v-if="hasActionableIssues">
          <div class="font-medium">
            {{ t('profit_loss_report.actionable.overview_warning_title') }}
          </div>
          <ul class="list-disc pl-4 my-1">
            <li v-if="missingAcquisitionsCount > 0">
              {{ t('profit_loss_report.actionable.overview_warning_acquisitions', { count: missingAcquisitionsCount }) }}
            </li>
            <li v-if="missingPricesCount > 0">
              {{ t('profit_loss_report.actionable.overview_warning_prices', { count: missingPricesCount }) }}
            </li>
          </ul>
          {{ t('profit_loss_report.actionable.overview_warning') }}
        </div>
        <div v-if="eventsSkippedCount > 0">
          {{ t('profit_loss_report.actionable.skipped_no_rule', { count: eventsSkippedCount }) }}
        </div>
      </RuiAlert>
      <RuiAlert
        v-else-if="showStaleDetails"
        type="info"
      >
        {{ t('profit_loss_report.actionable.stale_details') }}
      </RuiAlert>
      <ProfitLossOverview
        :report="selectedReport"
        :symbol="settings.profitCurrency"
        :loading="loading"
      />
      <ProfitLossEvents
        v-model:report-events="reportEvents"
        :report="selectedReport"
        :refreshing="refreshing"
      />
    </div>
  </div>
</template>
