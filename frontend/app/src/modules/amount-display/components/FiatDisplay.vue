<script setup lang="ts">
/**
 * FiatDisplay - Display a fiat value in user's currency.
 *
 * If `from` is provided, converts from source currency to user's currency.
 * If `from` is omitted, displays value as-is in user's currency.
 * If `currency` is provided, displays using that currency's symbol instead of user's.
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
 *
 * @example
 * <FiatDisplay :value="reportValue" :currency="report.profitCurrency" />
 */
import type { BigNumber } from '@rotki/common';
import type { SymbolDisplay, Timestamp } from '@/modules/amount-display/types';
import { useAmountDisplaySettings, useFiatConversion, useScrambledValue } from '@/modules/amount-display';
import { type Currency, useCurrencies } from '@/types/currencies';
import AmountDisplayBase from './AmountDisplayBase.vue';

interface Props {
  /** The fiat value to display */
  value: BigNumber | undefined;
  /** Source currency code - if omitted, no conversion is performed */
  from?: string;
  /** Timestamp for historic rate lookup */
  timestamp?: Timestamp;
  /** Apply PnL coloring (green positive, red negative) */
  pnl?: boolean;
  /** Loading state */
  loading?: boolean;
  /** How to display the currency: 'symbol' (default, e.g. €), 'ticker' (e.g. EUR), or 'none' */
  symbol?: SymbolDisplay;
  /** Override the displayed currency (e.g., 'USD', 'EUR'). If omitted, uses user's main currency. */
  currency?: string;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<Props>(), {
  currency: undefined,
  from: '',
  pnl: false,
  symbol: 'symbol',
  timestamp: undefined,
});

const { from, timestamp, value, loading: loadingProp } = toRefs(props);

// Composables
const { converted, loading } = useFiatConversion({
  from,
  timestamp,
  value,
});
const { currency: userCurrency } = useAmountDisplaySettings();
const { findCurrency } = useCurrencies();
const { scrambledValue } = useScrambledValue({ value: converted });

// Computed
const resolvedCurrency = computed<Currency>(() => {
  if (props.currency)
    return findCurrency(props.currency);
  return get(userCurrency);
});

const displaySymbol = computed<string>(() => {
  const currency = get(resolvedCurrency);
  switch (props.symbol) {
    case 'none':
      return '';
    case 'ticker':
      return currency.tickerSymbol;
    case 'symbol':
    default:
      return currency.unicodeSymbol;
  }
});
</script>

<template>
  <AmountDisplayBase
    :value="scrambledValue"
    :symbol="displaySymbol"
    :loading="loading || loadingProp"
    :pnl="pnl"
    v-bind="$attrs"
  >
    <template #tooltip>
      <slot name="tooltip" />
    </template>
  </AmountDisplayBase>
</template>
