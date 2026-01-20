<script setup lang="ts">
import type { NumberParts } from '@/modules/amount-display/composables/use-amount-formatter';

defineProps<{
  numberParts: NumberParts;
}>();

const ZERO_DISPLAY = '0';
</script>

<template>
  <template v-if="numberParts.full">
    {{ numberParts.full }}
  </template>
  <template v-else>
    <span>{{ numberParts.whole }}</span>
    <span>{{ numberParts.separator }}</span>
    <span>{{ ZERO_DISPLAY }}</span>
    <span
      class="text-[0.8em] align-bottom relative top-[0.35em]"
      data-cy="amount-display-subscript"
    >
      {{ numberParts.leadingZeros }}
    </span>
    <span>
      {{ numberParts.significantDigits }}
    </span>
  </template>
</template>
