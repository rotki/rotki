<script setup lang="ts">
import { type PropType } from 'vue';
import { type ProfitLossReportPeriod } from '@/types/reports';

defineProps({
  period: {
    required: true,
    type: Object as PropType<ProfitLossReportPeriod>
  }
});
</script>

<template>
  <VRow>
    <VCol>
      <i18n
        tag="div"
        path="profit_loss_report.report_period"
        class="text-h5 mt-6"
      >
        <template #start>
          <DateDisplay :timestamp="period.start" class="font-medium" />
        </template>
        <template #end>
          <DateDisplay :timestamp="period.end" class="font-medium" />
        </template>
      </i18n>
    </VCol>
  </VRow>
</template>
