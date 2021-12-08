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
    <reports-table v-show="!isRunning" class="mt-8" />
    <div v-if="loaded && !isRunning && !reportError.message">
      <v-row>
        <v-col>
          <i18n
            tag="div"
            path="profit_loss_report.report_period"
            class="text-h5 mt-6"
          >
            <template #start>
              <date-display
                no-timezone
                :timestamp="report.start"
                class="font-weight-medium"
              />
            </template>
            <template #end>
              <date-display
                no-timezone
                :timestamp="report.end"
                class="font-weight-medium"
              />
            </template>
          </i18n>
        </v-col>
      </v-row>
      <card v-if="showUpgradeMessage" class="mt-4 mb-8">
        <i18n
          tag="div"
          path="profit_loss_report.upgrade"
          class="text-subtitle-1"
        >
          <template #processed>
            <span class="font-weight-medium">{{ report.entriesFound }}</span>
          </template>
          <template #start>
            <date-display
              :timestamp="report.firstProcessedTimestamp"
              class="font-weight-medium"
              no-timezone
            />
          </template>
        </i18n>
        <i18n tag="div" path="profit_loss_report.upgrade2">
          <template #link>
            <base-external-link
              :text="$t('upgrade_row.rotki_premium')"
              :href="$interop.premiumURL"
            />
          </template>
        </i18n>
      </card>
      <accounting-settings-display
        :accounting-settings="accountingSettings"
        class="mt-4"
      />
      <v-btn
        class="profit_loss_report__export-csv mt-8"
        depressed
        color="primary"
        @click="exportCSV()"
      >
        {{
          $interop.isPackaged
            ? $t('profit_loss_report.export_csv')
            : $t('profit_loss_report.download_csv')
        }}
      </v-btn>
      <profit-loss-overview class="mt-8" :overview="report.overview" />
      <profit-loss-events class="mt-8" />
    </div>
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
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import AccountingSettingsDisplay from '@/components/profitloss/AccountingSettingsDisplay.vue';
import Generate from '@/components/profitloss/Generate.vue';
import ProfitLossEvents from '@/components/profitloss/ProfitLossEvents.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import ReportsTable from '@/components/profitloss/ReportsTable.vue';
import { setupTaskStatus } from '@/composables/tasks';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useReports } from '@/store/reports';
import { Message } from '@/store/types';
import { useStore } from '@/store/utils';
import { TaskType } from '@/types/task-type';

export default defineComponent({
  name: 'ProfitLossReport',
  components: {
    BaseExternalLink,
    ErrorScreen,
    ProfitLossOverview,
    ProfitLossEvents,
    ReportsTable,
    AccountingSettingsDisplay,
    ProgressScreen,
    Generate
  },
  setup() {
    const { isTaskRunning } = setupTaskStatus();
    const reportsStore = useReports();
    const { reportError, report } = storeToRefs(reportsStore);
    const { generateReport, createCsv } = reportsStore;
    const isRunning = isTaskRunning(TaskType.TRADE_HISTORY);
    const store = useStore();

    const showMessage = (description: string) => {
      store.commit('setMessage', {
        title: i18n.t('profit_loss_report.csv_export_error').toString(),
        description: description
      } as Message);
    };

    const exportCSV = async () => {
      try {
        if (interop.isPackaged && api.defaultBackend) {
          const directory = await interop.openDirectory(
            i18n.t('profit_loss_report.select_directory').toString()
          );
          if (!directory) {
            return;
          }
          await createCsv(directory);
        } else {
          const { success, message } = await api.downloadCSV();
          if (!success) {
            showMessage(
              message ?? i18n.t('profit_loss_report.download_failed').toString()
            );
          }
        }
      } catch (e: any) {
        showMessage(e.message);
      }
    };

    const showUpgradeMessage = computed(
      () =>
        report.value.entriesLimit > 0 &&
        report.value.entriesLimit < report.value.entriesFound
    );

    return {
      processingState: computed(() => reportsStore.processingState),
      progress: computed(() => reportsStore.progress),
      loaded: computed(() => reportsStore.loaded),
      isRunning,
      report,
      showUpgradeMessage,
      reportError,
      generateReport,
      exportCSV
    };
  }
});
</script>
