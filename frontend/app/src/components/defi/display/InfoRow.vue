<script setup lang="ts">
import { BigNumber } from '@rotki/common';

defineProps({
  loading: { required: false, type: Boolean },
  title: { required: true, type: String },
  value: {
    required: false,
    type: BigNumber,
    default: () => Zero
  },
  fiat: { required: false, type: Boolean }
});
</script>

<template>
  <div class="d-flex justify-space-between">
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
