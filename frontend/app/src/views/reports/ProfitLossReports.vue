<template>
  <v-container>
    <generate
      v-show="!isRunning && !reportError.message"
      @generate="generate($event)"
    />
    <error-screen
      v-if="!isRunning && reportError.message"
      class="mt-12"
      :message="reportError.message"
      :error="reportError.error"
      :title="$t('profit_loss_report.error.title')"
      :subtitle="$t('profit_loss_report.error.subtitle')"
    >
      <template #bottom>
        <v-btn text class="mt-2" @click="clearError()">
          {{ $t('profit_loss_reports.error.close') }}
        </v-btn>
      </template>
    </error-screen>
    <export-report-csv v-if="canExport && !isRunning && !reportError.message" />
    <reports-table v-show="!isRunning && !reportError.message" class="mt-8" />
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
import { useRouter } from '@/composables/common';
import { Routes } from '@/router/routes';
import { useReports } from '@/store/reports';
import { useTasks } from '@/store/tasks';
import { ProfitLossReportPeriod } from '@/types/reports';
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
    const { generateReport, clearError } = reportsStore;
    const isRunning = isTaskRunning(TaskType.TRADE_HISTORY);
    const canExport = computed(() => reports.value.entriesFound > 0);
    const router = useRouter();

    const generate = async (period: ProfitLossReportPeriod) => {
      const reportId = await generateReport(period);
      if (reportId > 0) {
        router.push(
          Routes.PROFIT_LOSS_REPORT.replace(':id', reportId.toString())
        );
      }
    };

    return {
      processingState: computed(() => reportsStore.processingState),
      progress: computed(() => reportsStore.progress),
      loaded: computed(() => reportsStore.loaded),
      canExport,
      isRunning,
      reportError,
      clearError,
      generate
    };
  }
});
</script>
