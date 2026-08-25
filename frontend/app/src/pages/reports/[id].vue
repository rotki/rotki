<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import AccountingSettingsDisplay from '@/modules/reports/AccountingSettingsDisplay.vue';
import ExportReportCsv from '@/modules/reports/ExportReportCsv.vue';
import ProfitLossEvents from '@/modules/reports/ProfitLossEvents.vue';
import ProfitLossOverview from '@/modules/reports/ProfitLossOverview.vue';
import ReportActionable from '@/modules/reports/ReportActionable.vue';
import ReportHeader from '@/modules/reports/ReportHeader.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import { useReportDetail } from '@/pages/reports/use-report-detail';

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

const {
  eventsSkippedCount,
  hasActionableIssues,
  initialOpenReportActionable,
  latest,
  loading,
  missingAcquisitionsCount,
  missingPricesCount,
  modelReportEvents,
  refreshing,
  regenerateReport,
  reportId,
  selectedReport,
  settings,
  showCompletenessWarning,
  showStaleDetails,
} = useReportDetail();
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
          data-testid="regenerate-report"
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
        data-testid="completeness-warning"
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
        data-testid="stale-details"
      >
        {{ t('profit_loss_report.actionable.stale_details') }}
      </RuiAlert>
      <ProfitLossOverview
        :report="selectedReport"
        :loading="loading"
      />
      <ProfitLossEvents
        v-model:report-events="modelReportEvents"
        :report="selectedReport"
        :refreshing="refreshing"
      />
    </div>
  </div>
</template>
