<script setup lang="ts">
import type { BalancePoint, BucketSeries } from '@/modules/balances/account-history/balance-series';
import { toCapitalCase } from '@rotki/common';
import { RuiButton, RuiButtonGroup, RuiCard } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed, ref } from 'vue';
import VChart from 'vue-echarts';
import { useI18n } from 'vue-i18n';
import { useAmountDisplaySettings } from '@/modules/assets/amount-display';
import { BalanceChartMode, useAccountBalanceChart } from '@/modules/balances/account-history/components/chart/use-account-balance-chart';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';

const { buckets, loading = false, total } = defineProps<{
  buckets: BucketSeries[];
  total: BalancePoint[];
  loading?: boolean;
}>();

/**
 * Shown in place of the chart, at the chart's size, so swapping between a message and the chart
 * does not move the page.
 */
defineSlots<{
  /** Controls shown in the header beside the mode switch, available even over a placeholder. */
  actions?: () => unknown;
  placeholder?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const mode = ref<BalanceChartMode>(BalanceChartMode.STACKED);

const { getLocationData } = useLocations();
const { getCounterpartyData } = useHistoryEventCounterpartyMappings();
const { shouldShowAmount } = useAmountDisplaySettings();

/** A bucket outside any protocol is the account's own wallet balance in that location. */
function bucketLabel(bucket: BucketSeries): string {
  const location = getLocationData(bucket.location)?.name ?? toCapitalCase(bucket.location);
  const holder = bucket.protocol ? get(getCounterpartyData(bucket.protocol)).label : t('account_history.chart.wallet');
  return `${location} · ${holder}`;
}

const { option } = useAccountBalanceChart({
  bucketLabel,
  buckets: () => buckets,
  mode,
  showAmounts: shouldShowAmount,
  total: () => total,
});

const modes = computed<{ value: BalanceChartMode; label: string }[]>(() => [
  { label: t('account_history.chart.stacked'), value: BalanceChartMode.STACKED },
  { label: t('account_history.chart.total'), value: BalanceChartMode.TOTAL },
]);
</script>

<template>
  <RuiCard data-testid="account-balance-chart">
    <template #custom-header>
      <div class="flex flex-wrap items-center justify-between gap-2 p-4 pb-0">
        <span class="text-h6">{{ t('account_history.chart.title') }}</span>
        <div class="flex flex-wrap items-center gap-2">
          <slot name="actions" />
          <RuiButtonGroup
            v-model="mode"
            variant="segmented"
            required
            size="sm"
            data-testid="account-balance-chart-mode"
          >
            <RuiButton
              v-for="item in modes"
              :key="item.value"
              :model-value="item.value"
              :disabled="!!$slots.placeholder"
              :data-testid="`account-balance-chart-mode-${item.value}`"
            >
              {{ item.label }}
            </RuiButton>
          </RuiButtonGroup>
        </div>
      </div>
    </template>
    <div
      v-if="$slots.placeholder"
      class="h-72 flex items-center justify-center text-center px-4"
      data-testid="account-balance-chart-placeholder"
    >
      <slot name="placeholder" />
    </div>
    <VChart
      v-else
      class="w-full h-72!"
      :option="option"
      :update-options="{ notMerge: true }"
      :loading="loading"
      autoresize
    />
  </RuiCard>
</template>
