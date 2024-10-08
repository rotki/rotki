<script setup lang="ts">
import { type Message, Priority, Severity } from '@rotki/common';
import { TaskType } from '@/types/task-type';
import { displayDateFormatter } from '@/data/date-formatter';
import FileUpload from '@/components/import/FileUpload.vue';
import { NoteLocation } from '@/types/notes';
import { Routes } from '@/router/routes';
import type { ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/types/reports';
import type { TaskMeta } from '@/types/task';

definePage({
  meta: {
    noteLocation: NoteLocation.PROFIT_LOSS_REPORTS,
  },
});

const { isTaskRunning, awaitTask } = useTaskStore();
const reportsStore = useReportsStore();
const { reportError } = storeToRefs(reportsStore);
const { generateReport, clearError, exportReportData, fetchReports } = reportsStore;
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
        start: Number.parseInt(start),
        end: Number.parseInt(end),
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
      title: t('profit_loss_reports.notification.title'),
      message: t('profit_loss_reports.notification.message', {
        start: formatDate(period.start),
        end: formatDate(period.end),
      }),
      display: true,
      severity: Severity.INFO,
      priority: Priority.ACTION,
      action: {
        label: t('profit_loss_reports.notification.action'),
        action,
      },
    });
  }
}

const { setMessage } = useMessageStore();

async function exportData({ start, end }: ProfitLossReportPeriod) {
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
        title: t('profit_loss_reports.debug.export_message.title'),
        description: result
          ? t('profit_loss_reports.debug.export_message.success')
          : t('profit_loss_reports.debug.export_message.failure'),
        success: !!result,
      };
    }
    else {
      downloadFileByTextContent(JSON.stringify(result, null, 2), 'pnl_debug.json', 'application/json');
    }
  }
  catch (error: any) {
    message = {
      title: t('profit_loss_reports.debug.export_message.title'),
      description: error.message,
      success: false,
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
      title: t('profit_loss_reports.debug.import_message.title'),
      description: t('profit_loss_reports.debug.import_message.failure', {
        message,
      }),
    });
  }
  else {
    setMessage({
      title: t('profit_loss_reports.debug.import_message.title'),
      description: t('profit_loss_reports.debug.import_message.success'),
      success: true,
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
