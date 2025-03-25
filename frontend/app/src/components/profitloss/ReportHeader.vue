<script setup lang="ts">
import type { ProfitLossReportPeriod } from '@/types/reports';
import DateDisplay from '@/components/display/DateDisplay.vue';

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
        :timestamp="period.start ?? 0"
        class="font-medium"
      />
    </template>
    <template #end>
      <DateDisplay
        :timestamp="period.end ?? 0"
        class="font-medium"
      />
    </template>
  </i18n-t>
</template>
