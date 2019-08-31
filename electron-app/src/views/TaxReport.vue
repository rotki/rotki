<template>
  <v-container>
    <v-layout column class="tax-report">
      <v-layout>
        <v-flex xs12>
          <h1>Tax Report</h1>
        </v-flex>
      </v-layout>
    </v-layout>
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
    <div v-if="isRunning">
      <v-layout>
        <v-flex>
          <h2 class="text-center">Generating Report</h2>
        </v-flex>
      </v-layout>
      <v-layout>
        <v-flex>
          <v-progress-circular
            class="text-center"
            size="80"
            :value="progress"
          ></v-progress-circular>
        </v-flex>
      </v-layout>
      <v-layout>
        <v-flex>
          <p class="text-center">Please wait...</p>
        </v-flex>
      </v-layout>
    </div>
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

const mapTaskGetters = createNamespacedHelpers('tasks').mapGetters;
const { mapState, mapGetters } = createNamespacedHelpers('reports');
const mapSessionState = createNamespacedHelpers('session').mapState;

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
    return true; //this.isTaskRunning(TaskType.TRADE_HISTORY);
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
</style>
