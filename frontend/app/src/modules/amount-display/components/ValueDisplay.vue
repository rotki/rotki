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
import type { FormatOptions } from '@/modules/amount-display/types';
import { useScrambledValue } from '@/modules/amount-display';
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

const props = withDefaults(defineProps<Props>(), {
  format: undefined,
  loading: false,
  noTooltip: false,
});

const { value, noScramble } = toRefs(props);

// Apply scrambling for privacy
const { scrambledValue } = useScrambledValue({ value, noScramble });

// Merge format with amountRoundingMode
const formatWithRounding = computed<FormatOptions>(() => ({
  ...props.format,
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
