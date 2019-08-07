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
import { create_task } from '@/legacy/monitor';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';

@Component({
  components: { MessageDialog, Generate }
})
export default class TaxReport extends Vue {
  errorMessage: string = '';

  mounted() {}

  generate(event: TaxReportEvent) {
    this.$rpc
      .process_trade_history_async(event.start, event.end)
      .then(result => {
        create_task(
          result.task_id,
          'process_trade_history',
          'Create tax report',
          false,
          true
        );
      })
      .catch((reason: Error) => {
        this.errorMessage = reason.message;
      });
  }
}
</script>

<style scoped></style>
