<template>
  <div class="d-flex justify-space-between">
    <div>
      {{ title }}
    </div>
    <slot>
      <amount-display
        :fiat-currency="fiat ? 'USD' : undefined"
        :value="value"
        :loading="loading"
        :show-currency="fiat ? 'none' : 'ticker'"
      />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Zero } from '@/utils/bignumbers';

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
