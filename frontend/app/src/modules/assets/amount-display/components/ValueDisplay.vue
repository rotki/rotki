<script setup lang="ts">
/**
 * Displays a raw numeric value, with no symbol, scrambled for privacy when the setting is on.
 *
 * @remarks
 * Rounds by `amountRoundingMode`, which is usually `ROUND_UP`.
 *
 * @example
 * ```vue
 * <ValueDisplay :value="bigNumberify(1.5)" />
 * <ValueDisplay :value="amount" :format="{ integer: true }" />
 * ```
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

const { scrambledValue } = useScrambledValue({ value: () => value, noScramble: () => noScramble });

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
