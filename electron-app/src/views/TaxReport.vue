<template>
  <v-container>
    <v-col cols="12" class="tax-report">
      <v-row>
        <h1>Tax Report</h1>
      </v-row>
    </v-col>
    <generate @generate="generate($event)"></generate>
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
    <v-col v-if="isRunning" cols="12" class="tax-report__progress">
      <v-row align="center" justify="center">
        <h2 class="text-center">Generating Report</h2>
      </v-row>
      <v-row
        align="center"
        justify="center"
        class="tax-report__progress__progress"
      >
        <v-progress-circular
          class="text-center"
          size="80"
          color="primary"
          :value="progress"
        >
          {{ progress }} %
        </v-progress-circular>
      </v-row>
      <v-row align="center" justify="center">
        <p class="text-center">Please wait...</p>
      </v-row>
    </v-col>
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

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
const { mapState, mapGetters } = createNamespacedHelpers('reports');
const { mapState: mapSessionState } = createNamespacedHelpers('session');

@Component({
  components: { TaxReportEvents, TaxReportOverview, MessageDialog, Generate },
  computed: {
    ...mapTaskGetters(['isTaskRunning']),
    ...mapGetters(['progress']),
    ...mapState(['loaded']),
    ...mapSessionState(['currency'])
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
      async filePaths => {
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

.tax-report__progress {
  margin-top: 20px;
  height: 100%;
  min-height: 300px;
}

.tax-report__progress__progress {
  min-height: 150px;
}
</style>
