<template>
  <v-container>
    <v-col cols="12" class="tax-report">
      <v-row>
        <h1>Tax Report</h1>
      </v-row>
    </v-col>
    <generate v-show="!isRunning" @generate="generate($event)"></generate>
    <div v-if="loaded && !isRunning">
      <v-btn
        class="tax-report__export-csv"
        depressed
        color="primary"
        @click="exportCSV()"
      >
        Export CSV
      </v-btn>
      <tax-report-overview class="tax-report__section"></tax-report-overview>
      <tax-report-events class="tax-report__section"></tax-report-events>
    </div>
    <progress-screen v-if="isRunning" :progress="progress">
      <template #message>
        Please wait while your report is generated...
      </template>

      Your report generation might take a while depending on the amount of
      trades and actions you performed during the selected period.
    </progress-screen>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Generate from '@/components/taxreport/Generate.vue';
import { TaxReportEvent } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { TaskType } from '@/model/task';
import { createNamespacedHelpers } from 'vuex';
import { remote } from 'electron';
import TaxReportOverview from '@/components/taxreport/TaxReportOverview.vue';
import TaxReportEvents from '@/components/taxreport/TaxReportEvents.vue';
import { Currency } from '@/model/currency';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
const { mapState, mapGetters } = createNamespacedHelpers('reports');
const { mapGetters: mapSessionGetters } = createNamespacedHelpers('session');

@Component({
  components: {
    ProgressScreen,
    TaxReportEvents,
    TaxReportOverview,
    MessageDialog,
    Generate
  },
  computed: {
    ...mapTaskGetters(['isTaskRunning']),
    ...mapGetters(['progress']),
    ...mapState(['loaded']),
    ...mapSessionGetters(['currency'])
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

  exportCSV() {
    remote.dialog.showOpenDialog(
      {
        title: 'Select a directory',
        properties: ['openDirectory']
      },
      async (filePaths: string[] | undefined) => {
        if (!filePaths) {
          return;
        }
        await this.$store.dispatch('reports/createCSV', filePaths[0]);
      }
    );
  }
}
</script>

<style scoped lang="scss">
.tax-report__section {
  margin-top: 20px;
}

.tax-report__export-csv {
  margin-top: 20px;
}
</style>
