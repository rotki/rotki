<template>
  <v-container>
    <base-page-header :text="$t('profit_loss_report.title')">
      <v-tooltip top>
        <template #activator="{ on, attrs }">
          <v-btn
            text
            fab
            depressed
            v-bind="attrs"
            to="/settings/accounting"
            v-on="on"
          >
            <v-icon color="primary">mdi-cog</v-icon>
          </v-btn>
        </template>
        <span>{{ $t('profit_loss_report.settings_tooltip') }}</span>
      </v-tooltip>
    </base-page-header>
    <generate v-show="!isRunning" @generate="generate($event)" />
    <error-screen
      v-if="!isRunning && reportError.message"
      class="mt-12"
      :message="reportError.message"
      :error="reportError.error"
      :title="$t('profit_loss_report.error.title')"
      :subtitle="$t('profit_loss_report.error.subtitle')"
    />
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
                :timestamp="reportPeriod.start"
                class="font-weight-medium"
              />
            </template>
            <template #end>
              <date-display
                no-timezone
                :timestamp="reportPeriod.end"
                class="font-weight-medium"
              />
            </template>
          </i18n>
        </v-col>
      </v-row>
      <accounting-settings-display
        :accounting-settings="accountingSettings"
        class="mt-4"
      />
      <v-btn
        class="profit_loss_report__export-csv mt-4"
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
      <profit-loss-overview class="mt-4" />
      <profit-loss-events class="mt-4" />
    </div>
    <progress-screen v-if="isRunning" :progress="progress">
      <template #message>
        <div v-if="processingState" class="medium title mb-4">
          {{ processingState }}
        </div>
        {{ $t('profit_loss_report.loading_message') }}
      </template>
      {{ $t('profit_loss_report.loading_hint') }}
    </progress-screen>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import AccountingSettingsDisplay from '@/components/profitloss/AccountingSettingsDisplay.vue';
import Generate from '@/components/profitloss/Generate.vue';
import ProfitLossEvents from '@/components/profitloss/ProfitLossEvents.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import { ReportError, ReportPeriod } from '@/store/reports/types';
import { Message } from '@/store/types';
import { AccountingSettings, ProfitLossPeriod } from '@/typing/types';

@Component({
  components: {
    ErrorScreen,
    ProfitLossOverview,
    ProfitLossEvents,
    AccountingSettingsDisplay,
    BasePageHeader,
    ProgressScreen,
    Generate
  },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('reports', ['progress', 'processingState']),
    ...mapState('reports', [
      'loaded',
      'accountingSettings',
      'reportPeriod',
      'reportError'
    ]),
    ...mapGetters('session', ['currency'])
  }
})
export default class ProfitLossReport extends Vue {
  isTaskRunning!: (type: TaskType) => boolean;
  loaded!: boolean;
  currency!: Currency;
  progress!: string;
  processingState!: string;
  accountingSettings!: AccountingSettings;
  reportPeriod!: ReportPeriod;
  reportError!: ReportError;

  get isRunning(): boolean {
    return this.isTaskRunning(TaskType.TRADE_HISTORY);
  }

  generate(event: ProfitLossPeriod) {
    this.$store.commit('reports/currency', this.currency.ticker_symbol);
    this.$store.dispatch('reports/generate', event);
  }

  async exportCSV() {
    try {
      if (this.$interop.isPackaged) {
        const directory = await this.$interop.openDirectory(
          this.$t('profit_loss_report.select_directory').toString()
        );
        if (!directory) {
          return;
        }
        await this.$store.dispatch('reports/createCSV', directory);
      } else {
        const { success, message } = await this.$api.downloadCSV();
        if (!success) {
          this.showMessage(
            message ?? this.$t('profit_loss_report.download_failed').toString()
          );
        }
      }
    } catch (e) {
      const description = e.message;
      this.showMessage(description);
    }
  }

  private showMessage(description: string) {
    this.$store.commit('setMessage', {
      title: this.$t('profit_loss_report.csv_export_error').toString(),
      description: description
    } as Message);
  }
}
</script>
