<script setup lang="ts">
import type { ProfitLossEvent, Report } from '@/types/reports';
import DateDisplay from '@/components/display/DateDisplay.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import AccountingSettingsDisplay from '@/components/profitloss/AccountingSettingsDisplay.vue';
import ExportReportCsv from '@/components/profitloss/ExportReportCsv.vue';
import ProfitLossEvents from '@/components/profitloss/ProfitLossEvents.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import ReportActionable from '@/components/profitloss/ReportActionable.vue';
import ReportHeader from '@/components/profitloss/ReportHeader.vue';
import { defaultReportEvents, useReportsStore } from '@/store/reports';
import { NoteLocation } from '@/types/notes';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

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
const { fetchReports, getActionableItems, isLatestReport } = reportsStore;

const router = useRouter();
const route = useRoute<'/reports/[id]'>();
const currentRoute = get(route);
const reportId = Number(currentRoute.params.id as string);
const latest = isLatestReport(reportId);

const selectedReport = computed<Report>(() => get(reports).entries.find(item => item.identifier === reportId)!);
const settings = computed(() => get(selectedReport).settings);

const reportEvents = ref(defaultReportEvents());

const { found, limit, total } = getCollectionData<ProfitLossEvent>(reportEvents);
const { showUpgradeRow } = setupEntryLimit(limit, found, total);

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
      <RuiAlert
        v-if="showUpgradeRow"
        type="warning"
      >
        <i18n-t
          scope="global"
          tag="div"
          keypath="profit_loss_report.upgrade"
          class="text-subtitle-1"
        >
          <template #processed>
            <span class="font-medium">{{ reportEvents.found }}</span>
          </template>
          <template #start>
            <DateDisplay
              :timestamp="selectedReport.firstProcessedTimestamp"
              class="font-medium"
            />
          </template>
        </i18n-t>
        <i18n-t
          scope="global"
          tag="div"
          keypath="profit_loss_report.upgrade2"
        >
          <template #link>
            <ExternalLink
              color="primary"
              :text="t('upgrade_row.rotki_premium')"
              premium
            />
          </template>
        </i18n-t>
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
            <RuiIcon name="lu-refresh-ccw" />
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
