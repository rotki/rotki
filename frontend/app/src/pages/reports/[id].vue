<script setup lang="ts">
import type { Report } from '@/modules/reports/report-types';
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
const { reports } = storeToRefs(reportsStore);
const { isLatestReport } = reportsStore;
const { fetchReports, getActionableItems } = useReportOperations();

const router = useRouter();
const route = useRoute<'/reports/[id]'>();
const currentRoute = get(route);
const reportId = Number(String(currentRoute.params.id));
const latest = isLatestReport(reportId);

const selectedReport = computed<Report>(() => get(reports).entries.find(item => item.identifier === reportId)!);
const settings = computed(() => get(selectedReport).settings);

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
