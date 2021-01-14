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
    <div v-if="loaded && !isRunning">
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
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import AccountingSettingsDisplay from '@/components/profitloss/AccountingSettingsDisplay.vue';
import Generate from '@/components/profitloss/Generate.vue';
import ProfitLossEvents from '@/components/profitloss/ProfitLossEvents.vue';
import ProfitLossOverview from '@/components/profitloss/ProfitLossOverview.vue';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import { ReportPeriod } from '@/store/reports/types';
import { Message } from '@/store/types';
import { AccountingSettings, ProfitLossPeriod } from '@/typing/types';

@Component({
  components: {
    ProfitLossOverview,
    ProfitLossEvents,
    AccountingSettingsDisplay,
    BasePageHeader,
    ProgressScreen,
    Generate
  },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('reports', ['progress']),
    ...mapState('reports', ['loaded', 'accountingSettings', 'reportPeriod']),
    ...mapGetters('session', ['currency'])
  }
})
export default class ProfitLossReport extends Vue {
  isTaskRunning!: (type: TaskType) => boolean;
  loaded!: boolean;
  currency!: Currency;
  progress!: number;
  accountingSettings!: AccountingSettings;
  reportPeriod!: ReportPeriod;

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
          this.$tc('profit_loss_report.select_directory')
        );
        if (!directory) {
          return;
        }
        await this.$store.dispatch('reports/createCSV', directory);
      } else {
        const { success, message } = await this.$api.downloadCSV();
        if (!success) {
          this.showMessage(
            message ?? this.$tc('profit_loss_report.download_failed')
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
      title: this.$tc('profit_loss_report.csv_export_error'),
      description: description
    } as Message);
  }
}
</script>
