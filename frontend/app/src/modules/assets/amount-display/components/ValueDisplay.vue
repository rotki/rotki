<script setup lang="ts">
/**
 * ValueDisplay - Display a raw numeric value.
 *
 * Shows a scrambled numeric value without any symbol.
 * Uses amountRoundingMode for rounding (typically ROUND_UP).
 *
 * @example
 * <ValueDisplay :value="bigNumberify(1.5)" />
 *
 * @example
 * <ValueDisplay :value="amount" :format="{ integer: true }" />
 */
import type { BigNumber } from '@rotki/common';
import type { FormatOptions } from '@/modules/assets/amount-display/types';
import { useScrambledValue } from '@/modules/assets/amount-display';
import AmountDisplayBase from './AmountDisplayBase.vue';

interface Props {
  /** The value to display */
  value: BigNumber;
  /** Format options */
  format?: FormatOptions;
  /** Loading state */
  loading?: boolean;
  /** Disable tooltip */
  noTooltip?: boolean;
  /** Skip scrambling even when privacy mode is enabled */
  noScramble?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const { value, noScramble, format } = defineProps<Props>();

// Apply scrambling for privacy
const { scrambledValue } = useScrambledValue({ value: () => value, noScramble: () => noScramble });

// Merge format with amountRoundingMode
const formatWithRounding = computed<FormatOptions>(() => ({
  ...format,
  rounding: 'amount',
}));
</script>

<template>
  <AmountDisplayBase
    :value="scrambledValue"
    :loading="loading"
    :format="formatWithRounding"
    :no-tooltip="noTooltip"
    v-bind="$attrs"
  />
</template>
