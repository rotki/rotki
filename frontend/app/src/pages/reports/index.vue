<script setup lang="ts">
import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/types/reports';
import type { TaskMeta } from '@/types/task';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import ReportGenerator from '@/components/profitloss/ReportGenerator.vue';
import ReportsTable from '@/components/profitloss/ReportsTable.vue';
import { useReportsApi } from '@/composables/api/reports';
import { useInterop } from '@/composables/electron-interop';
import { displayDateFormatter } from '@/data/date-formatter';
import { Routes } from '@/router/routes';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useReportsStore } from '@/store/reports';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { NoteLocation } from '@/types/notes';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { downloadFileByTextContent } from '@/utils/download';
import { type Message, Priority, Severity } from '@rotki/common';

definePage({
  meta: {
    noteLocation: NoteLocation.PROFIT_LOSS_REPORTS,
  },
});

const { awaitTask, isTaskRunning } = useTaskStore();
const reportsStore = useReportsStore();
const { reportError } = storeToRefs(reportsStore);
const { clearError, exportReportData, fetchReports, generateReport } = reportsStore;
const isRunning = isTaskRunning(TaskType.TRADE_HISTORY);
const importDataDialog = ref<boolean>(false);
const reportDebugData = ref<File>();
const importDataLoading = ref<boolean>(false);
const reportDebugDataUploader = ref<InstanceType<typeof FileUpload>>();

const router = useRouter();
const route = useRoute();

const { t } = useI18n();
const { appSession, getPath, openDirectory } = useInterop();

onMounted(async () => {
  const query = get(route).query;
  if (query.regenerate) {
    const start: string = (query.start as string) || '';
    const end: string = (query.end as string) || '';

    if (start && end) {
      const period = {
        end: Number.parseInt(end),
        start: Number.parseInt(start),
      };

      await router.replace({ query: {} });
      await generate(period);
    }
  }
});

const { pinned } = storeToRefs(useAreaVisibilityStore());

const { notify } = useNotificationsStore();

const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

async function generate(period: ProfitLossReportPeriod) {
  if (get(pinned)?.name === 'report-actionable-card')
    set(pinned, null);

  const formatDate = (timestamp: number) =>
    displayDateFormatter.format(new Date(timestamp * 1000), get(dateDisplayFormat));

  const reportId = await generateReport(period);

  const action = () => {
    router.push({
      name: '/reports/[id]',
      params: {
        id: reportId.toString(),
      },
      query: {
        openReportActionable: 'true',
      },
    });
  };

  if (reportId > 0) {
    if (route.path === Routes.PROFIT_LOSS_REPORTS) {
      action();
      return;
    }
    notify({
      action: {
        action,
        label: t('profit_loss_reports.notification.action'),
      },
      display: true,
      message: t('profit_loss_reports.notification.message', {
        end: formatDate(period.end),
        start: formatDate(period.start),
      }),
      priority: Priority.ACTION,
      severity: Severity.INFO,
      title: t('profit_loss_reports.notification.title'),
    });
  }
}

const { setMessage } = useMessageStore();

async function exportData({ end, start }: ProfitLossReportPeriod) {
  const payload: ProfitLossReportDebugPayload = {
    fromTimestamp: start,
    toTimestamp: end,
  };

  let message: Message | null = null;

  try {
    if (appSession) {
      const directoryPath = await openDirectory(t('common.select_directory'));
      if (!directoryPath)
        return;

      payload.directoryPath = directoryPath;
    }

    const result = await exportReportData(payload);

    if (appSession) {
      message = {
        description: result
          ? t('profit_loss_reports.debug.export_message.success')
          : t('profit_loss_reports.debug.export_message.failure'),
        success: !!result,
        title: t('profit_loss_reports.debug.export_message.title'),
      };
    }
    else {
      downloadFileByTextContent(JSON.stringify(result, null, 2), 'pnl_debug.json', 'application/json');
    }
  }
  catch (error: any) {
    message = {
      description: error.message,
      success: false,
      title: t('profit_loss_reports.debug.export_message.title'),
    };
  }

  if (message)
    setMessage(message);
}

const { importReportData, uploadReportData } = useReportsApi();

async function importData() {
  if (!isDefined(reportDebugData))
    return;

  set(importDataLoading, true);

  let success: boolean;
  let message = '';

  const taskType = TaskType.IMPORT_PNL_REPORT_DATA;

  const file = get(reportDebugData);

  try {
    const path = getPath(file);
    const { taskId } = path
      ? await importReportData(path)
      : await uploadReportData(file);

    const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, {
      title: t('profit_loss_reports.debug.import_message.title'),
    });
    success = result;
  }
  catch (error: any) {
    if (isTaskCancelled(error))
      return fetchReports();

    message = error.message;
    success = false;
  }

  if (!success) {
    setMessage({
      description: t('profit_loss_reports.debug.import_message.failure', {
        message,
      }),
      title: t('profit_loss_reports.debug.import_message.title'),
    });
  }
  else {
    setMessage({
      description: t('profit_loss_reports.debug.import_message.success'),
      success: true,
      title: t('profit_loss_reports.debug.import_message.title'),
    });
    await fetchReports();
  }

  set(importDataLoading, false);
  set(importDataDialog, false);
  get(reportDebugDataUploader)?.removeFile();
  set(reportDebugData, undefined);
}

const processingState = computed(() => reportsStore.processingState);
const progress = computed(() => reportsStore.progress);
</script>

<template>
  <div class="container">
    <ReportGenerator
      v-show="!isRunning && !reportError.message"
      @generate="generate($event)"
      @export-data="exportData($event)"
      @import-data="importDataDialog = true"
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
      v-model="importDataDialog"
      max-width="600"
    >
      <RuiCard>
        <template #header>
          {{ t('profit_loss_reports.debug.import_data_dialog.title') }}
        </template>
        <FileUpload
          ref="reportDebugDataUploader"
          v-model="reportDebugData"
          source="json"
          file-filter=".json"
        />
        <template #footer>
          <div class="grow" />
          <RuiButton
            variant="text"
            color="primary"
            @click="importDataDialog = false"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :disabled="!reportDebugData"
            :loading="importDataLoading"
            @click="importData()"
          >
            {{ t('common.actions.import') }}
          </RuiButton>
        </template>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
