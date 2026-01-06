<script setup lang="ts">
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import ReportGenerator from '@/components/profitloss/ReportGenerator.vue';
import ReportsTable from '@/components/profitloss/ReportsTable.vue';
import { useInterop } from '@/composables/electron-interop';
import { useReportsPageActions } from '@/pages/reports/use-reports-page-actions';
import { Routes } from '@/router/routes';
import { useReportsStore } from '@/store/reports';
import { useTaskStore } from '@/store/tasks';
import { NoteLocation } from '@/types/notes';
import { TaskType } from '@/types/task-type';

definePage({
  meta: {
    noteLocation: NoteLocation.PROFIT_LOSS_REPORTS,
  },
});

const { useIsTaskRunning } = useTaskStore();
const reportsStore = useReportsStore();
const { reportError } = storeToRefs(reportsStore);
const { clearError } = reportsStore;
const isRunning = useIsTaskRunning(TaskType.TRADE_HISTORY);
const importDataDialog = ref<boolean>(false);
const reportDebugData = ref<File>();
const reportDebugDataUploader = ref<InstanceType<typeof FileUpload>>();

const router = useRouter();
const route = useRoute();

const { t } = useI18n({ useScope: 'global' });
const { getPath } = useInterop();

function navigateToReport(reportId: number): void {
  if (route.path === Routes.PROFIT_LOSS_REPORTS) {
    router.push({
      name: '/reports/[id]',
      params: {
        id: reportId.toString(),
      },
      query: {
        openReportActionable: 'true',
      },
    });
  }
}

const { exportData, generate, importData, importDataLoading } = useReportsPageActions({
  getPath,
  onNavigateToReport: navigateToReport,
  reportDebugData,
});

onMounted(async () => {
  const query = get(route).query;
  if (!query.regenerate) {
    return;
  }

  const start: string = (query.start as string) || '';
  const end: string = (query.end as string) || '';
  if (!(start && end)) {
    return;
  }
  const period = {
    end: Number.parseInt(end),
    start: Number.parseInt(start),
  };
  await router.replace({ query: {} });
  await generate(period);
});

async function handleImportComplete(): Promise<void> {
  await importData();
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
            @click="handleImportComplete()"
          >
            {{ t('common.actions.import') }}
          </RuiButton>
        </template>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
