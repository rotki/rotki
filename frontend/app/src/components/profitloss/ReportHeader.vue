<script setup lang="ts">
import { type ProfitLossReportPeriod } from '@/types/reports';

defineProps<{
  period: ProfitLossReportPeriod;
}>();
</script>

<template>
  <i18n tag="div" path="profit_loss_report.report_period" class="text-h5 mt-6">
    <template #start>
      <DateDisplay :timestamp="period.start" class="font-medium" />
    </template>
    <template #end>
      <DateDisplay :timestamp="period.end" class="font-medium" />
    </template>
  </i18n>
</template>
