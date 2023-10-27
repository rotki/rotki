<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

withDefaults(
  defineProps<{
    loading?: boolean;
    title: string;
    value?: BigNumber;
    fiat?: boolean;
  }>(),
  {
    loading: false,
    value: () => Zero,
    fiat: false
  }
);
</script>

<template>
  <div class="flex justify-between">
    <div>
      {{ title }}
    </div>
    <slot>
      <AmountDisplay
        :fiat-currency="fiat ? 'USD' : undefined"
        :value="value"
        :loading="loading"
        :show-currency="fiat ? 'none' : 'ticker'"
      />
    </slot>
  </div>
</template>
