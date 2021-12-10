<template>
  <v-container>
    <generate v-show="!isRunning" @generate="generateReport($event)" />
    <error-screen
      v-if="!isRunning && reportError.message"
      class="mt-12"
      :message="reportError.message"
      :error="reportError.error"
      :title="$t('profit_loss_report.error.title')"
      :subtitle="$t('profit_loss_report.error.subtitle')"
    />
    <export-report-csv v-if="canExport" />
    <reports-table v-show="!isRunning" class="mt-8" />
    <progress-screen v-if="isRunning" :progress="progress">
      <template #message>
        <div v-if="processingState" class="medium text-h6 mb-4">
          {{ processingState }}
        </div>
        {{ $t('profit_loss_report.loading_message') }}
      </template>
      {{ $t('profit_loss_report.loading_hint') }}
    </progress-screen>
  </v-container>
</template>

<script lang="ts">
import { computed, defineComponent } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ExportReportCsv from '@/components/profitloss/ExportReportCsv.vue';
import Generate from '@/components/profitloss/Generate.vue';
import ReportsTable from '@/components/profitloss/ReportsTable.vue';
import { useReports } from '@/store/reports';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export default defineComponent({
  name: 'ProfitLossReports',
  components: {
    ExportReportCsv,
    ErrorScreen,
    ReportsTable,
    ProgressScreen,
    Generate
  },
  setup() {
    const { isTaskRunning } = useTasks();
    const reportsStore = useReports();
    const { reportError, reports } = storeToRefs(reportsStore);
    const { generateReport } = reportsStore;
    const isRunning = isTaskRunning(TaskType.TRADE_HISTORY);
    const canExport = computed(() => reports.value.entriesFound > 0);

    return {
      processingState: computed(() => reportsStore.processingState),
      progress: computed(() => reportsStore.progress),
      loaded: computed(() => reportsStore.loaded),
      canExport,
      isRunning,
      reportError,
      generateReport
    };
  }
});
</script>
