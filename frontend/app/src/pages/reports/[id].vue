<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { Routes } from '@/router/routes';
import { type SelectedReport } from '@/types/reports';

defineOptions({
  name: 'ReportDetail'
});

const loading = ref(true);
const refreshing = ref(false);
const reportsStore = useReportsStore();
const { report, reports } = storeToRefs(reportsStore);

const { fetchReports, fetchReport, clearReport, isLatestReport } = reportsStore;
const router = useRouter();
const route = useRoute();
let firstPage = true;

const selectedReport: ComputedRef<SelectedReport> = computed(() => get(report));
const settings = computed(() => get(selectedReport).settings);

const initialOpenReportActionable = ref<boolean>(false);

const currentRoute = get(route);
const reportId = Number.parseInt(currentRoute.params.id as string);
const latest = isLatestReport(reportId);

const { t } = useI18n();

onMounted(async () => {
  if (get(reports).entries.length === 0) {
    await fetchReports();
  }
  const success = await fetchReport(reportId);
  if (!success) {
    await router.push(Routes.PROFIT_LOSS_REPORTS);
  }

  if (get(route).query.openReportActionable) {
    set(initialOpenReportActionable, true);
    await router.replace({ query: {} });
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

const regenerateReport = async () => {
  const { start, end } = get(report);
  await router.push({
    path: Routes.PROFIT_LOSS_REPORTS,
    query: {
      regenerate: 'true',
      start: start.toString(),
      end: end.toString()
    }
  });
};
</script>

<template>
  <ProgressScreen v-if="loading">
    {{ t('profit_loss_report.loading') }}
  </ProgressScreen>
  <div v-else class="container">
    <div class="flex flex-col gap-8">
      <ReportHeader :period="report" />
      <RuiAlert v-if="showUpgradeMessage" type="warning">
        <i18n
          tag="div"
          path="profit_loss_report.upgrade"
          class="text-subtitle-1"
        >
          <template #processed>
            <span class="font-medium">{{ report.entriesFound }}</span>
          </template>
          <template #start>
            <DateDisplay
              :timestamp="report.firstProcessedTimestamp"
              class="font-medium"
            />
          </template>
        </i18n>
        <i18n tag="div" path="profit_loss_report.upgrade2">
          <template #link>
            <ExternalLink :text="t('upgrade_row.rotki_premium')" premium />
          </template>
        </i18n>
      </RuiAlert>
      <AccountingSettingsDisplay :accounting-settings="settings" />
      <div class="flex gap-2">
        <template v-if="latest">
          <ExportReportCsv />
          <ReportActionable
            :report="selectedReport"
            :initial-open="initialOpenReportActionable"
            @regenerate="regenerateReport()"
          />
        </template>
        <RuiButton
          color="primary"
          variant="outlined"
          @click="regenerateReport()"
        >
          <template #prepend>
            <RuiIcon name="refresh-line" />
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
        :report="selectedReport"
        :refreshing="refreshing"
        @update:page="onPage($event)"
      />
    </div>
  </div>
</template>
