<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import AccountingSettingsDisplay from '@/modules/reports/AccountingSettingsDisplay.vue';
import ExportReportCsv from '@/modules/reports/ExportReportCsv.vue';
import ProfitLossEvents from '@/modules/reports/ProfitLossEvents.vue';
import ProfitLossOverview from '@/modules/reports/ProfitLossOverview.vue';
import ReportActionable from '@/modules/reports/ReportActionable.vue';
import ReportHeader from '@/modules/reports/ReportHeader.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
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
  <TablePageLayout :aria-busy="loading || undefined">
    <template #title>
      <RuiSkeletonLoader
        v-if="loading"
        class="w-72 h-5"
      />
      <ReportHeader
        v-else
        :period="{ start: selectedReport.startTs, end: selectedReport.endTs }"
      />
    </template>
    <template
      v-if="!loading"
      #buttons
    >
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
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('profit_loss_report.actionable.actions.regenerate_report') }}
      </RuiButton>
      <ExportReportCsv :report-id="reportId" />
    </template>

    <div
      v-if="loading"
      class="flex flex-col gap-6"
      :aria-label="t('profit_loss_report.loading')"
      data-testid="report-detail-skeleton"
    >
      <RuiSkeletonLoader class="h-40 rounded-rui-card" />
      <RuiSkeletonLoader class="h-28 rounded-rui-card" />
      <RuiSkeletonLoader class="h-96 rounded-rui-card" />
    </div>
    <div
      v-else
      class="flex flex-col gap-6"
    >
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
      <AccountingSettingsDisplay :accounting-settings="settings" />
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
  </TablePageLayout>
</template>
