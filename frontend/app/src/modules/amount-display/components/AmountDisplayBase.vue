<script setup lang="ts">
/**
 * AmountDisplayBase - Internal component for rendering formatted amounts.
 *
 * This is a pure display component - no scrambling logic.
 * Scrambling should be handled by parent components.
 *
 * Use one of the higher-level components instead:
 * - FiatDisplay - for fiat values (with scrambling)
 * - AssetValueDisplay - for asset values (with scrambling)
 * - AssetAmountDisplay - for asset amounts (with scrambling)
 * - ValueDisplay - for raw values (with scrambling)
 *
 * Styling: Use CSS classes via $attrs (e.g., class="text-2xl")
 */
import type { BigNumber } from '@rotki/common';
import type { FormatOptions } from '@/modules/amount-display/types';
import CopyTooltip from '@/components/helper/CopyTooltip.vue';
import { useAmountDisplaySettings, useAmountFormatter } from '@/modules/amount-display';
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

const props = withDefaults(defineProps<Props>(), {
  format: undefined,
  loading: false,
  noTooltip: false,
  noTruncate: false,
  pnl: false,
  symbol: '',
});

const { value } = toRefs(props);

// Extract format options
const isInteger = computed<boolean>(() => props.format?.integer ?? false);

// Get display settings
const { currencyLocation, shouldShowAmount } = useAmountDisplaySettings();

// Format the value for display
const roundingType = computed(() => props.format?.rounding ?? 'value');

const {
  comparisonSymbol,
  isNaN,
  numberParts,
  tooltip,
} = useAmountFormatter({
  integer: isInteger,
  rounding: roundingType,
  value,
});

// Copy value for clipboard
const copyValue = computed<string>(() => {
  if (get(isNaN)) {
    return '-';
  }
  return get(value).toString();
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
    data-cy="amount-display"
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
        data-cy="display-amount"
        :value="copyValue"
      >
        <FormattedNumber :number-parts="numberParts" />
        <template #tooltip>
          <slot name="tooltip">
            <div v-if="tooltip">
              {{ tooltip }}
            </div>
          </slot>
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
