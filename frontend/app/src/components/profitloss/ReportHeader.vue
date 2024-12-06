<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';
import type { ProfitLossReportPeriod } from '@/types/reports';

defineProps<{
  period: ProfitLossReportPeriod;
}>();
</script>

<template>
  <i18n-t
    tag="div"
    keypath="profit_loss_report.report_period"
    class="text-h5 mt-6"
  >
    <template #start>
      <DateDisplay
        :timestamp="period.start"
        class="font-medium"
      />
    </template>
    <template #end>
      <DateDisplay
        :timestamp="period.end"
        class="font-medium"
      />
    </template>
  </i18n-t>
</template>
