<script setup lang="ts">
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import type { BigNumber } from '@rotki/common';

withDefaults(
  defineProps<{
    loading?: boolean;
    title: string;
    value?: BigNumber;
    fiat?: boolean;
  }>(),
  {
    fiat: false,
    loading: false,
    value: () => Zero,
  },
);
</script>

<template>
  <div class="flex justify-between">
    <div>
      {{ title }}
    </div>
    <slot>
      <AmountDisplay
        class="font-bold"
        :fiat-currency="fiat ? 'USD' : undefined"
        :value="value"
        :loading="loading"
        :show-currency="fiat ? 'none' : 'ticker'"
      />
    </slot>
  </div>
</template>
