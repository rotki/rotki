<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import StakingHeadlineBalance from '@/modules/staking/components/StakingHeadlineBalance.vue';

export interface StakingTotal {
  key: string;
  label: string;
  amount: BigNumber;
  testid: string;
}

/**
 * A staking page's totals, in one asset priced at its current price. From `md` up each total is a
 * card of its own, as the RuiCard beside them would draw it; on a phone they share one card, a row
 * each, so three tall cards no longer fill the first screen before the table.
 */
defineProps<{
  asset: string;
  totals: StakingTotal[];
  loading: boolean;
}>();
</script>

<template>
  <div
    class="grid gap-4 md:grid-cols-3 max-md:gap-0 max-md:rounded-rui-card max-md:border max-md:border-rui-divider max-md:bg-rui-surface"
  >
    <div
      v-for="total in totals"
      :key="total.key"
      class="md:rounded-rui-card md:border md:border-rui-divider md:bg-rui-surface max-md:[&+&]:border-t max-md:border-rui-divider"
    >
      <div class="p-4 text-base font-semibold text-rui-text max-md:pb-1 max-md:text-sm max-md:font-normal max-md:text-rui-text-secondary">
        {{ total.label }}
      </div>
      <StakingHeadlineBalance
        class="p-4 max-md:pt-1 text-sm/6"
        :data-testid="total.testid"
        :asset="asset"
        :value="{ amount: total.amount }"
        :loading="loading"
        calculate-value
      />
    </div>
  </div>
</template>
