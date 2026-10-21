<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import ReportGenerator from '@/modules/reports/ReportGenerator.vue';
import ReportsTable from '@/modules/reports/ReportsTable.vue';
import { useReportsStore } from '@/modules/reports/use-reports-store';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { type Activity, ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { useTaskController } from '@/modules/task-center/use-task-controller';
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

/**
 * Whether the page is asking to confirm a stop. The question sits in place of the button, so it
 * goes away with the work: once the report settles there is nothing left to stop.
 */
const confirmingStop = ref<boolean>(false);

const { useActivity } = useTaskCenter();
const { cancel } = useTaskController();

const processingState = computed(() => reportsStore.processingState);
const progress = computed(() => reportsStore.progress);
const reportActivity = useActivity(ActivityKind.PNL_REPORT);

function stopGeneration(activity: Activity): void {
  set(confirmingStop, false);
  startPromise(cancel(activity));
}

watch(() => get(reportActivity)?.cancellable, (cancellable) => {
  if (!cancellable)
    set(confirmingStop, false);
});

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
      <div
        v-if="reportActivity?.cancellable"
        class="flex justify-center mt-6"
      >
        <div
          v-if="confirmingStop"
          class="flex items-center gap-1 pl-3 rounded-sm bg-rui-warning/10"
          data-testid="report-generation-stop-confirm"
        >
          <span class="text-sm">{{ t('task_dock.panel.stop_confirm') }}</span>
          <RuiButton
            variant="text"
            size="sm"
            data-testid="report-generation-keep-running"
            @click="confirmingStop = false"
          >
            {{ t('task_dock.panel.keep_running') }}
          </RuiButton>
          <RuiButton
            variant="text"
            color="error"
            size="sm"
            data-testid="report-generation-stop"
            @click="stopGeneration(reportActivity)"
          >
            {{ t('task_dock.panel.stop') }}
          </RuiButton>
        </div>
        <RuiButton
          v-else
          variant="outlined"
          data-testid="report-generation-cancel"
          @click="confirmingStop = true"
        >
          <template #prepend>
            <RuiIcon name="lu-circle-stop" />
          </template>
          {{ t('profit_loss_report.cancel_generation') }}
        </RuiButton>
      </div>
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
