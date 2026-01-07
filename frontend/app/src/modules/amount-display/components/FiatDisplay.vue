<script setup lang="ts">
/**
 * FiatDisplay - Display a fiat value in user's currency.
 *
 * If `from` is provided, converts from source currency to user's currency.
 * If `from` is omitted, displays value as-is in user's currency.
 * Values are scrambled for privacy when enabled in settings.
 *
 * @example
 * <FiatDisplay :value="valueInUserCurrency" />
 *
 * @example
 * <FiatDisplay :value="usdValue" from="USD" />
 *
 * @example
 * <FiatDisplay :value="profit" from="USD" pnl />
 *
 * @example
 * <FiatDisplay :value="amount" symbol="ticker" />
 */
import type { BigNumber } from '@rotki/common';
import type { FormatOptions, SymbolDisplay, Timestamp } from '@/modules/amount-display/types';
import { useAmountDisplaySettings, useFiatConversion, useScrambledValue } from '@/modules/amount-display';
import AmountDisplayBase from './AmountDisplayBase.vue';

interface Props {
  /** The fiat value to display */
  value: BigNumber | undefined;
  /** Source currency code - if omitted, no conversion is performed */
  from?: string;
  /** Timestamp for historic rate lookup */
  timestamp?: Timestamp;
  /** Format options */
  format?: FormatOptions;
  /** Apply PnL coloring (green positive, red negative) */
  pnl?: boolean;
  /** How to display the currency: 'symbol' (default, e.g. €), 'ticker' (e.g. EUR), or 'none' */
  symbol?: SymbolDisplay;
  /** Disable truncation on currency symbol */
  noTruncate?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<Props>(), {
  format: undefined,
  from: '',
  noTruncate: false,
  pnl: false,
  symbol: 'symbol',
  timestamp: undefined,
});

const { from, timestamp, value } = toRefs(props);

// Composables
const { converted, loading } = useFiatConversion({
  from,
  timestamp,
  value,
});
const { currency } = useAmountDisplaySettings();
const { scrambledValue } = useScrambledValue({ value: converted });

// Computed
const displaySymbol = computed<string>(() => {
  switch (props.symbol) {
    case 'none':
      return '';
    case 'ticker':
      return get(currency).tickerSymbol;
    case 'symbol':
    default:
      return get(currency).unicodeSymbol;
  }
});
</script>

<template>
  <AmountDisplayBase
    :value="scrambledValue"
    :symbol="displaySymbol"
    :loading="loading"
    :pnl="pnl"
    :format="format"
    :no-truncate="noTruncate"
    v-bind="$attrs"
  >
    <template #tooltip>
      <slot name="tooltip" />
    </template>
  </AmountDisplayBase>
</template>
