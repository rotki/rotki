<script setup lang="ts">
import type { HistoricalBalanceDivergenceEvent } from '@/modules/history/balances/types';
import { divergenceGap, GapUnit } from '@/modules/history/balances/divergence-gap';

/** The stretch between the last matching and first diverged events, where the faulty event sits. */
const { from, to } = defineProps<{
  from: HistoricalBalanceDivergenceEvent;
  to: HistoricalBalanceDivergenceEvent;
}>();

const { t } = useI18n({ useScope: 'global' });

const gap = computed<ReturnType<typeof divergenceGap>>(() => divergenceGap(from.timestamp, to.timestamp));

const gapLabel = computed<string>(() => {
  const { count, unit } = get(gap);
  if (unit === GapUnit.DAYS)
    return t('balance_divergence.apart.days', { count }, count);
  if (unit === GapUnit.HOURS)
    return t('balance_divergence.apart.hours', { count }, count);
  return t('balance_divergence.apart.minutes', { count }, count);
});
</script>

<template>
  <div
    class="flex flex-wrap items-center justify-center gap-x-2 gap-y-0.5 rounded-sm bg-rui-warning/10 px-2 py-1 text-xs text-rui-warning"
    data-testid="divergence-gap"
  >
    <span class="inline-flex items-center gap-1 font-medium">
      <RuiIcon
        name="lu-search"
        size="12"
      />
      {{ t('balance_divergence.search_window') }}
    </span>
    <span class="inline-flex items-center gap-1">
      <RuiTooltip
        v-if="!gap.exact"
        :open-delay="200"
        :options="{ placement: 'top' }"
      >
        <template #activator>
          <RuiIcon
            name="lu-equal-approximately"
            size="12"
            data-testid="divergence-gap-approximate"
          />
        </template>
        {{ t('balance_divergence.apart.rounded') }}
      </RuiTooltip>
      {{ gapLabel }}
    </span>
    <span data-testid="divergence-block-range">
      {{ t('balance_divergence.block_range', { from: from.blockNumber, to: to.blockNumber }) }}
    </span>
    <RuiTooltip
      :open-delay="200"
      :options="{ placement: 'top' }"
      class="inline-flex"
    >
      <template #activator>
        <RuiIcon
          name="lu-info"
          size="12"
          data-testid="divergence-gap-hint"
        />
      </template>
      {{ t('data_issues.detail.divergence_next_step') }}
    </RuiTooltip>
  </div>
</template>
