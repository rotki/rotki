<script setup lang="ts">
import type { ProfitLossReportPeriod } from '@/modules/reports/report-types';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

defineProps<{
  period: ProfitLossReportPeriod;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <nav class="flex flex-wrap items-center text-sm font-medium">
    <RouterLink
      :to="{ name: '/reports/' }"
      class="text-rui-text-secondary hover:text-rui-text"
      data-testid="report-breadcrumb-list"
    >
      {{ t('navigation_menu.profit_loss_report') }}
    </RouterLink>
    <RuiIcon
      name="lu-chevron-right"
      size="16"
      class="mx-2 text-rui-text-secondary"
    />
    <i18n-t
      scope="global"
      tag="h1"
      keypath="profit_loss_report.report_period"
      class="text-sm font-medium text-rui-text"
      data-testid="report-period"
    >
      <template #start>
        <DateDisplay
          no-time
          :timestamp="period.start"
        />
      </template>
      <template #end>
        <DateDisplay
          no-time
          :timestamp="period.end"
        />
      </template>
    </i18n-t>
  </nav>
</template>
