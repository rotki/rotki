<template>
  <v-container>
    <base-page-header :text="$t('tax_report.title')">
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
        <span>{{ $t('tax_report.settings_tooltip') }}</span>
      </v-tooltip>
    </base-page-header>
    <generate v-show="!isRunning" @generate="generate($event)" />
    <div v-if="loaded && !isRunning">
      <v-btn
        class="tax-report__export-csv"
        depressed
        color="primary"
        @click="exportCSV()"
      >
        {{
          $interop.isPackaged
            ? $t('tax_report.export_csv')
            : $t('tax_report.download_csv')
        }}
      </v-btn>
      <tax-report-overview class="tax-report__section" />
      <tax-report-events class="tax-report__section" />
    </div>
    <progress-screen v-if="isRunning" :progress="progress">
      <template #message>{{ $t('tax_report.loading_message') }}</template>
      {{ $t('tax_report.loading_hint') }}
    </progress-screen>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import Generate from '@/components/taxreport/Generate.vue';
import TaxReportEvents from '@/components/taxreport/TaxReportEvents.vue';
import TaxReportOverview from '@/components/taxreport/TaxReportOverview.vue';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import { Message } from '@/store/types';
import { TaxReportEvent } from '@/typing/types';

@Component({
  components: {
    BasePageHeader,
    ProgressScreen,
    TaxReportEvents,
    TaxReportOverview,
    Generate
  },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('reports', ['progress']),
    ...mapState('reports', ['loaded']),
    ...mapGetters('session', ['currency'])
  }
})
export default class TaxReport extends Vue {
  isTaskRunning!: (type: TaskType) => boolean;
  loaded!: boolean;
  currency!: Currency;
  progress!: number;

  get isRunning(): boolean {
    return this.isTaskRunning(TaskType.TRADE_HISTORY);
  }

  generate(event: TaxReportEvent) {
    this.$store.commit('reports/currency', this.currency.ticker_symbol);
    this.$store.dispatch('reports/generate', event);
  }

  async exportCSV() {
    try {
      if (this.$interop.isPackaged) {
        const directory = await this.$interop.openDirectory(
          this.$tc('tax_report.select_directory')
        );
        if (!directory) {
          return;
        }
        await this.$store.dispatch('reports/createCSV', directory);
      } else {
        const { success, message } = await this.$api.downloadCSV();
        if (!success) {
          this.showMessage(message ?? this.$tc('tax_report.download_failed'));
        }
      }
    } catch (e) {
      const description = e.message;
      this.showMessage(description);
    }
  }

  private showMessage(description: string) {
    this.$store.commit('setMessage', {
      title: this.$tc('tax_report.csv_export_error'),
      description: description
    } as Message);
  }
}
</script>

<style scoped lang="scss">
.tax-report {
  &__section {
    margin-top: 20px;
  }

  &__export-csv {
    margin-top: 20px;
  }
}
</style>
