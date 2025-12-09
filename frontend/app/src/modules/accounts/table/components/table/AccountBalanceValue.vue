<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';

interface Props {
  includedValue: BigNumber | undefined;
  loading: boolean;
  value: BigNumber;
}

defineProps<Props>();
</script>

<template>
  <div class="flex flex-col items-end justify-end">
    <div
      v-if="includedValue && !loading"
      class="text-xs"
    >
      <AmountDisplay
        v-if="includedValue"
        force-currency
        :value="includedValue"
        show-currency="symbol"
      />
      /
    </div>
    <AmountDisplay
      data-cy="usd-value"
      class="font-medium"
      force-currency
      :value="value"
      show-currency="symbol"
      :loading="loading"
    />
  </div>
</template>
