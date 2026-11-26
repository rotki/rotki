<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { RuiButton, RuiCard, RuiDialog, RuiFileUpload, RuiIcon } from '@rotki/ui-library';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import ReportGenerationStop from '@/modules/reports/ReportGenerationStop.vue';
import ReportGenerator from '@/modules/reports/ReportGenerator.vue';
import ReportsTable from '@/modules/reports/ReportsTable.vue';
import { useReportsStore } from '@/modules/reports/use-reports-store';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
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

const {
  exportData,
  generate,
  handleImportComplete,
  importDataLoading,
  isRunning,
  modelImportDataDialog,
  modelReportDebugData,
} = useReportsPage();

const processingState = computed(() => reportsStore.processingState);
const progress = computed(() => reportsStore.progress);

const accountingSettingsRoute: RouteLocationRaw = { name: '/settings/accounting/' };
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.profit_loss_report')]">
    <template #buttons>
      <RouterLink :to="accountingSettingsRoute">
        <RuiButton
          variant="outlined"
          color="primary"
          data-testid="report-accounting-settings"
        >
          <template #prepend>
            <RuiIcon name="lu-settings" />
          </template>
          {{ t('profit_loss_report.settings') }}
        </RuiButton>
      </RouterLink>
    </template>

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
      class="mt-4"
    />
    <ProgressScreen
      v-if="isRunning"
      :progress="progress"
    >
      <template #message>
        <span
          v-if="processingState"
          class="block text-base font-medium text-rui-text mb-1"
        >
          {{ processingState }}
        </span>
        <span class="block text-sm text-rui-text-secondary">
          {{ t('profit_loss_report.loading_message') }}
        </span>
      </template>
      <span class="block max-w-xl text-sm text-rui-text-secondary">
        {{ t('profit_loss_report.loading_hint') }}
      </span>
      <ReportGenerationStop />
    </ProgressScreen>
    <RuiDialog
      v-model="modelImportDataDialog"
      max-width="560"
    >
      <RuiCard>
        <template #header>
          {{ t('profit_loss_reports.debug.import_data_dialog.title') }}
        </template>
        <RuiFileUpload
          v-model="modelReportDebugData"
          accept=".json"
          :disabled="importDataLoading"
          :upload-text="t('file_upload.dropzone.prefix')"
          :click-to-upload-text="t('file_upload.dropzone.choose')"
          :replace-text="t('file_upload.dropzone.replace')"
          details="hidden"
          data-testid="report-debug-data-file"
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
  </TablePageLayout>
</template>
