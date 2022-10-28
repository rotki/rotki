<template>
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
            :timestamp="period.start"
            class="font-weight-medium"
          />
        </template>
        <template #end>
          <date-display
            no-timezone
            :timestamp="period.end"
            class="font-weight-medium"
          />
        </template>
      </i18n>
    </v-col>
  </v-row>
</template>
<script setup lang="ts">
import { PropType } from 'vue';
import { ProfitLossReportPeriod } from '@/types/reports';

defineProps({
  period: {
    required: true,
    type: Object as PropType<ProfitLossReportPeriod>
  }
});
</script>
