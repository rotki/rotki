<script setup lang="ts">
/**
 * Internal component for rendering a formatted amount. Style it with classes through `$attrs`.
 *
 * @remarks
 * Pure display, with **no scrambling of its own** — rendering a user value through this directly
 * leaks it when privacy mode is on. Reach for a wrapper that scrambles: `FiatDisplay`,
 * `AssetValueDisplay`, `AssetAmountDisplay` or `ValueDisplay`.
 */
import type { BigNumber } from '@rotki/common';
import type { FormatOptions } from '@/modules/assets/amount-display/types';
import { useAmountDisplaySettings, useAmountFormatter } from '@/modules/assets/amount-display';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';
import AmountCurrencySymbol from './AmountCurrencySymbol.vue';
import FormattedNumber from './FormattedNumber.vue';

interface Props {
  /** The value to display (should be pre-scrambled if needed) */
  value: BigNumber;
  /** Symbol to display (e.g., '$', 'USD'), or empty string for no symbol */
  symbol?: string;
  /** Format options (integer, decimals, isFiatValue) */
  format?: FormatOptions;
  /** Apply PnL coloring (green for positive, red for negative) */
  pnl?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Disable truncation on symbol */
  noTruncate?: boolean;
  /** Disable tooltip */
  noTooltip?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const { value, format, symbol = '' } = defineProps<Props>();

defineSlots<{
  tooltip: () => any;
}>();

const isInteger = computed<boolean>(() => format?.integer ?? false);

const { currencyLocation, shouldShowAmount } = useAmountDisplaySettings();

const roundingType = computed(() => format?.rounding ?? 'value');

const {
  comparisonSymbol,
  isNaN,
  numberParts,
  tooltip,
} = useAmountFormatter({
  decimals: () => format?.decimals,
  integer: isInteger,
  rounding: roundingType,
  value: () => value,
});

const copyValue = computed<string>(() => {
  if (get(isNaN)) {
    return '-';
  }
  return value.toString();
});
</script>

<template>
  <span
    :class="[
      {
        'blur': !shouldShowAmount,
        'text-rui-success': pnl && value.gt(0),
        'text-rui-error': pnl && value.lt(0),
        'skeleton min-h-5 min-w-[3.5rem] max-w-[4rem] after:content-[\'\\200B\']': loading,
      },
    ]"
    class="inline-flex items-center gap-1 transition duration-200 rounded-lg max-w-full"
    data-testid="amount-display"
    v-bind="$attrs"
  >
    <template v-if="!loading">
      <template v-if="comparisonSymbol">
        {{ comparisonSymbol }}
      </template>

      <AmountCurrencySymbol
        v-if="symbol && currencyLocation === 'before'"
        :symbol="symbol"
        :no-truncate="noTruncate"
      />

      <CopyTooltip
        :disabled="!shouldShowAmount || noTooltip"
        :tooltip="tooltip"
        data-testid="display-amount"
        :value="copyValue"
      >
        <FormattedNumber :number-parts="numberParts" />
        <template #tooltip>
          <slot name="tooltip" />
          <div v-if="tooltip">
            {{ tooltip }}
          </div>
        </template>
      </CopyTooltip>

      <AmountCurrencySymbol
        v-if="symbol && currencyLocation === 'after'"
        :symbol="symbol"
        :no-truncate="noTruncate"
      />
    </template>
  </span>
</template>
