import { TaskType } from "@/model/task"; import { TaskType } from
"@/model/task";
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
    <message-dialog
      title="Trade History Processing Error"
      :message="errorMessage"
      @dismiss="errorMessage = ''"
    ></message-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Generate from '@/components/taxreport/Generate.vue';
import { TaxReportEvent } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { createTask, TaskType } from '@/model/task';
import { createNamespacedHelpers } from 'vuex';
import remote = Electron.remote;

const { mapGetters } = createNamespacedHelpers('task');

@Component({
  components: { MessageDialog, Generate },
  computed: {
    ...mapGetters(['isTaskRunning'])
  }
})
export default class TaxReport extends Vue {
  errorMessage: string = '';

  isTaskRunning!: (type: TaskType) => boolean;

  messageTitle: string = '';
  messageDescription: string = '';
  messageSuccess: boolean = false;

  get isRunning(): boolean {
    return this.isTaskRunning(TaskType.TRADE_HISTORY);
  }

  mounted() {}

  generate(event: TaxReportEvent) {
    this.$rpc
      .process_trade_history_async(event.start, event.end)
      .then(result => {
        const task = createTask(
          result.task_id,
          TaskType.TRADE_HISTORY,
          'Create tax report',
          true
        );
      })
      .catch((reason: Error) => {
        this.errorMessage = reason.message;
      });
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
            this.messageTitle = 'Success';
            this.messageDescription = 'History exported to CVS successfully';
            this.messageSuccess = true;
          })
          .catch((reason: Error) => {
            this.messageTitle = 'Exporting History to CSV error';
            this.messageDescription = reason.message;
            this.messageSuccess = false;
          });
      }
    );
  }
}
</script>

<style scoped></style>
