<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';

interface Props {
  includedUsdValue: BigNumber | undefined;
  loading: boolean;
  usdValue: BigNumber;
}

defineProps<Props>();
</script>

<template>
  <div class="flex flex-col items-end justify-end">
    <div
      v-if="includedUsdValue && !loading"
      class="text-xs"
    >
      <AmountDisplay
        v-if="includedUsdValue"
        fiat-currency="USD"
        :value="includedUsdValue"
        show-currency="symbol"
      />
      /
    </div>
    <AmountDisplay
      data-cy="usd-value"
      class="font-medium"
      fiat-currency="USD"
      :value="usdValue"
      show-currency="symbol"
      :loading="loading"
    />
  </div>
</template>
