<script setup lang="ts">
/**
 * ValueDisplay - Display a raw numeric value with optional symbol.
 *
 * Shows a scrambled numeric value with optional symbol.
 * Uses amountRoundingMode for rounding (typically ROUND_UP).
 *
 * @example
 * <ValueDisplay :value="bigNumberify(1.5)" />
 *
 * @example
 * <ValueDisplay :value="amount" symbol="ETH" />
 */
import type { BigNumber } from '@rotki/common';
import type { FormatOptions } from '@/modules/amount-display/types';
import { useScrambledValue } from '@/modules/amount-display';
import AmountDisplayBase from './AmountDisplayBase.vue';

interface Props {
  /** The value to display */
  value: BigNumber;
  /** Optional symbol to display (e.g., 'ETH', '$'), or empty string for no symbol */
  symbol?: string;
  /** Format options */
  format?: FormatOptions;
  /** Apply PnL coloring (green positive, red negative) */
  pnl?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Disable truncation on symbol */
  noTruncate?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<Props>(), {
  format: undefined,
  loading: false,
  noTruncate: false,
  pnl: false,
  symbol: '',
});

const { value } = toRefs(props);

// Apply scrambling for privacy
const { scrambledValue } = useScrambledValue({ value });

// Merge format with amountRoundingMode
const formatWithRounding = computed<FormatOptions>(() => ({
  ...props.format,
  rounding: 'amount',
}));
</script>

<template>
  <AmountDisplayBase
    :value="scrambledValue"
    :symbol="symbol"
    :loading="loading"
    :pnl="pnl"
    :format="formatWithRounding"
    :no-truncate="noTruncate"
    v-bind="$attrs"
  />
</template>
