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
    <tax-report-overview v-if="loaded"></tax-report-overview>
    <v-overlay :value="isRunning">
      <h2>Generating Report</h2>
      <v-progress-circular size="60"></v-progress-circular>
      <p>Please wait...</p>
    </v-overlay>
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

const { mapGetters } = createNamespacedHelpers('tasks');
const { mapState } = createNamespacedHelpers('reports');

@Component({
  components: { TaxReportOverview, MessageDialog, Generate },
  computed: {
    ...mapGetters(['isTaskRunning']),
    ...mapState(['loaded'])
  }
})
export default class TaxReport extends Vue {
  isTaskRunning!: (type: TaskType) => boolean;
  loaded!: boolean;

  get isRunning(): boolean {
    return this.isTaskRunning(TaskType.TRADE_HISTORY);
  }

  mounted() {}

  generate(event: TaxReportEvent) {
    this.$store.dispatch('reports/generate', event);
  }

  promptDirectorySelection() {}

  exportCSV() {
    remote.dialog.showOpenDialog(
      {
        title: 'Select a directory',
        properties: ['openDirectory']
      },
      filePaths => {
        if (!filePaths) {
          return;
        }
        this.$rpc
          .export_processed_history_csv(filePaths[0])
          .then(() => {
            // this.messageTitle = 'Success';
            // this.messageDescription = 'History exported to CVS successfully';
            // this.messageSuccess = true;
          })
          .catch((reason: Error) => {
            // this.messageTitle = 'Exporting History to CSV error';
            // this.messageDescription = reason.message;
            // this.messageSuccess = false;
          });
      }
    );
  }
}
</script>

<style scoped></style>
