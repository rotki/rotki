<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import ReportGenerator from '@/modules/reports/ReportGenerator.vue';
import ReportsTable from '@/modules/reports/ReportsTable.vue';
import { useReportsStore } from '@/modules/reports/use-reports-store';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import FileUpload from '@/modules/user-data/FileUpload.vue';
import { useReportsPage } from '@/pages/reports/use-reports-page';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.profit_loss_report'), icon: 'lu-calculator', section: 1, order: 80, drawer: 'profit-loss-report' },
    noteLocation: NoteLocation.PROFIT_LOSS_REPORTS,
  },
});

const { t } = useI18n({ useScope: 'global' });

const reportsStore = useReportsStore();
const { reportError } = storeToRefs(reportsStore);
const { clearError } = reportsStore;

const reportDebugDataUploader = useTemplateRef<InstanceType<typeof FileUpload>>('reportDebugDataUploader');

const {
  exportData,
  generate,
  handleImportComplete,
  importDataLoading,
  isRunning,
  modelImportDataDialog,
  modelReportDebugData,
} = useReportsPage({
  onResetUploader: () => get(reportDebugDataUploader)?.removeFile(),
});

const processingState = computed(() => reportsStore.processingState);
const progress = computed(() => reportsStore.progress);
</script>

<template>
  <div class="container">
    <ReportGenerator
      v-show="!isRunning && !reportError.message"
      @generate="generate($event)"
      @export-data="exportData($event)"
      @import-data="modelImportDataDialog = true"
    />
    <ErrorScreen
      v-if="!isRunning && reportError.message"
      class="py-12"
      :message="reportError.message"
      :error="reportError.error"
      :title="t('profit_loss_report.error.title')"
      :subtitle="t('profit_loss_report.error.subtitle')"
    >
      <template #bottom>
        <RuiButton
          variant="text"
          class="mt-2"
          data-testid="clear-error"
          @click="clearError()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </ErrorScreen>
    <ReportsTable
      v-show="!isRunning && !reportError.message"
      class="mt-8"
    />
    <ProgressScreen
      v-if="isRunning"
      :progress="progress"
    >
      <template #message>
        <div
          v-if="processingState"
          class="medium text-h6 mb-4"
        >
          {{ processingState }}
        </div>
        {{ t('profit_loss_report.loading_message') }}
      </template>
      {{ t('profit_loss_report.loading_hint') }}
    </ProgressScreen>
    <RuiDialog
      v-model="modelImportDataDialog"
      max-width="600"
    >
      <RuiCard>
        <template #header>
          {{ t('profit_loss_reports.debug.import_data_dialog.title') }}
        </template>
        <FileUpload
          ref="reportDebugDataUploader"
          v-model="modelReportDebugData"
          source="json"
          file-filter=".json"
        />
        <template #footer>
          <div class="grow" />
          <RuiButton
            variant="text"
            color="primary"
            @click="modelImportDataDialog = false"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            data-testid="confirm-import"
            :disabled="!modelReportDebugData"
            :loading="importDataLoading"
            @click="handleImportComplete()"
          >
            {{ t('common.actions.import') }}
          </RuiButton>
        </template>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
