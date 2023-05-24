<script setup lang="ts">
import { type Message } from '@rotki/common/lib/messages';
import { Routes } from '@/router/routes';
import {
  type ProfitLossReportDebugPayload,
  type ProfitLossReportPeriod
} from '@/types/reports';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

const { isTaskRunning } = useTaskStore();
const reportsStore = useReportsStore();
const { reportError } = storeToRefs(reportsStore);
const { generateReport, clearError, exportReportData, fetchReports } =
  reportsStore;
const isRunning = isTaskRunning(TaskType.TRADE_HISTORY);
const importDataDialog = ref<boolean>(false);
const reportDebugData = ref<File | null>(null);
const importDataLoading = ref<boolean>(false);
const reportDebugDataUploader = ref<any>(null);

const router = useRouter();
const route = useRoute();

const { t } = useI18n();
const { appSession, openDirectory } = useInterop();

onMounted(async () => {
  const query = get(route).query;
  if (query.regenerate) {
    const start: string = (query.start as string) || '';
    const end: string = (query.end as string) || '';

    if (start && end) {
      const period = {
        start: Number.parseInt(start),
        end: Number.parseInt(end)
      };

      await router.replace({ query: {} });
      await generate(period);
    }
  }
});

const { pinned } = storeToRefs(useAreaVisibilityStore());

const generate = async (period: ProfitLossReportPeriod) => {
  if (get(pinned)?.name === 'report-actionable-card') {
    set(pinned, null);
  }

  const reportId = await generateReport(period);
  if (reportId > 0) {
    await router.push({
      path: Routes.PROFIT_LOSS_REPORT.replace(':id', reportId.toString()),
      query: {
        openReportActionable: 'true'
      }
    });
  }
};

const { setMessage } = useMessageStore();

const exportData = async ({ start, end }: ProfitLossReportPeriod) => {
  const payload: ProfitLossReportDebugPayload = {
    fromTimestamp: start,
    toTimestamp: end
  };

  let message: Message | null = null;

  try {
    const isLocal = appSession;
    if (isLocal) {
      const directoryPath =
        (await openDirectory(
          t('profit_loss_reports.debug.select_directory')
        )) || '';
      if (!directoryPath) {
        return;
      }
      payload['directoryPath'] = directoryPath;
    }

    const result = await exportReportData(payload);

    if (isLocal) {
      message = {
        title: t('profit_loss_reports.debug.export_message.title'),
        description: result
          ? t('profit_loss_reports.debug.export_message.success')
          : t('profit_loss_reports.debug.export_message.failure'),
        success: !!result
      };
    } else {
      const file = new Blob([JSON.stringify(result, null, 2)], {
        type: 'text/json'
      });
      const link = window.URL.createObjectURL(file);
      downloadFileByUrl(link, 'pnl_debug.json');
    }
  } catch (e: any) {
    message = {
      title: t('profit_loss_reports.debug.export_message.title'),
      description: e.message,
      success: false
    };
  }

  if (message) {
    setMessage(message);
  }
};

const { importReportData, uploadReportData } = useReportsApi();

const importData = async () => {
  if (!get(reportDebugData)) {
    return;
  }
  set(importDataLoading, true);

  let success: boolean;
  let message = '';

  const { awaitTask } = useTaskStore();
  const taskType = TaskType.IMPORT_PNL_REPORT_DATA;

  try {
    const { taskId } = appSession
      ? await importReportData(get(reportDebugData)!.path)
      : await uploadReportData(get(reportDebugData)!);

    const { result } = await awaitTask<boolean, TaskMeta>(taskId, taskType, {
      title: t('profit_loss_reports.debug.import_message.title')
    });
    success = result;
  } catch (e: any) {
    message = e.message;
    success = false;
  }

  if (!success) {
    setMessage({
      title: t('profit_loss_reports.debug.import_message.title'),
      description: t('profit_loss_reports.debug.import_message.failure', {
        message
      })
    });
  } else {
    setMessage({
      title: t('profit_loss_reports.debug.import_message.title'),
      description: t('profit_loss_reports.debug.import_message.success'),
      success: true
    });
    await fetchReports();
  }

  set(importDataLoading, false);
  get(reportDebugDataUploader)?.removeFile();
  set(reportDebugData, null);
};

const processingState = computed(() => reportsStore.processingState);
const progress = computed(() => reportsStore.progress);
</script>

<template>
  <v-container>
    <report-generator
      v-show="!isRunning && !reportError.message"
      @generate="generate($event)"
      @export-data="exportData($event)"
      @import-data="importDataDialog = true"
    />
    <error-screen
      v-if="!isRunning && reportError.message"
      class="mt-12"
      :message="reportError.message"
      :error="reportError.error"
      :title="t('profit_loss_report.error.title')"
      :subtitle="t('profit_loss_report.error.subtitle')"
    >
      <template #bottom>
        <v-btn text class="mt-2" @click="clearError()">
          {{ t('common.actions.close') }}
        </v-btn>
      </template>
    </error-screen>
    <reports-table v-show="!isRunning && !reportError.message" class="mt-8" />
    <progress-screen v-if="isRunning" :progress="progress">
      <template #message>
        <div v-if="processingState" class="medium text-h6 mb-4">
          {{ processingState }}
        </div>
        {{ t('profit_loss_report.loading_message') }}
      </template>
      {{ t('profit_loss_report.loading_hint') }}
    </progress-screen>
    <v-dialog v-model="importDataDialog" max-width="600">
      <card>
        <template #title>
          {{ t('profit_loss_reports.debug.import_data_dialog.title') }}
        </template>
        <div>
          <div class="py-2">
            <file-upload
              ref="reportDebugDataUploader"
              source="json"
              file-filter=".json"
              @selected="reportDebugData = $event"
            />
          </div>
          <div class="mt-2 d-flex justify-end">
            <v-btn class="mr-4" depressed @click="importDataDialog = false">
              {{ t('common.actions.cancel') }}
            </v-btn>
            <v-btn
              color="primary"
              :disabled="!reportDebugData"
              :loading="importDataLoading"
              @click="importData()"
            >
              {{ t('common.actions.import') }}
            </v-btn>
          </div>
        </div>
      </card>
    </v-dialog>
  </v-container>
</template>
