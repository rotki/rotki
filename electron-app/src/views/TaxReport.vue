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
    <v-col v-if="isRunning" cols="12" class="tax-report__progress">
      <v-row
        align="center"
        justify="center"
        class="font-weight-light tax-report__progress__percentage"
      >
        {{ progress }} %
      </v-row>
      <v-row
        align="center"
        justify="center"
        class="tax-report__progress__progress"
      >
        <v-col cols="10">
          <v-progress-linear
            class="text-center"
            rounded
            height="16"
            color="primary"
            :value="progress"
          >
          </v-progress-linear>
        </v-col>
      </v-row>
      <v-row align="center" justify="center">
        <p
          class="text-center font-weight-light tax-report__progress__description"
        >
          Please wait while your report is generated...
        </p>
      </v-row>
      <v-row align="center" justify="center">
        <v-col cols="4">
          <v-divider></v-divider>
        </v-col>
      </v-row>
      <v-row
        align="center"
        justify="center"
        class="tax-report__progress__warning"
      >
        <div class="font-weight-light subtitle-2">
          Your report generation might take a while depending on the amount of
          trades and actions you performed during the selected period.
        </div>
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
const { mapGetters: mapSessionGetters } = createNamespacedHelpers('session');

@Component({
  components: { TaxReportEvents, TaxReportOverview, MessageDialog, Generate },
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
  margin-top: 140px;
  height: 100%;
  min-height: 300px;
}

.tax-report__progress__progress {
  min-height: 80px;
}

.tax-report__progress__percentage {
  font-size: 46px;
}

.tax-report__progress__description {
  font-size: 16px;
}

.tax-report__progress__warning {
  margin-top: 30px;
}
</style>
