<script setup lang="ts">
/**
 * AssetValueDisplay - Display the fiat value of an asset amount.
 *
 * Calculates value as: amount × price, then displays in user's currency.
 * Alternatively, accepts a pre-calculated value to display directly.
 * Values are scrambled for privacy when enabled in settings.
 *
 * @example
 * <AssetValueDisplay asset="ETH" :amount="bigNumberify(2)" />
 *
 * @example
 * <AssetValueDisplay asset="ETH" :amount="balance" :timestamp="{ ms: eventTimeMs }" />
 *
 * @example
 * <AssetValueDisplay asset="ETH" :value="preCalculatedValue" />
 */
import type { FormatOptions, SymbolDisplay, Timestamp } from '@/modules/amount-display/types';
import { type BigNumber, Zero } from '@rotki/common';
import { useAmountDisplaySettings, useAssetValue, useOracleInfo, useScrambledValue } from '@/modules/amount-display';
import AmountDisplayBase from './AmountDisplayBase.vue';
import ManualPriceIndicator from './ManualPriceIndicator.vue';
import OracleBadge from './OracleBadge.vue';

interface Props {
  /** Asset identifier (e.g., 'ETH', 'BTC') */
  asset: string;
  /** Amount of the asset (used for calculation if value not provided) */
  amount?: BigNumber;
  /** Pre-calculated value to display (bypasses amount × price calculation) */
  value?: BigNumber;
  /** Known price per unit (optional, will lookup if not provided) */
  price?: BigNumber | null;
  /** Timestamp for historic price lookup */
  timestamp?: Timestamp;
  /** Format options */
  format?: FormatOptions;
  /** Apply PnL coloring (green positive, red negative) */
  pnl?: boolean;
  /** Loading state */
  loading?: boolean;
  /** How to display the currency: 'symbol' (default, e.g. €), 'ticker' (e.g. EUR), or 'none' */
  symbol?: SymbolDisplay;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<Props>(), {
  amount: undefined,
  format: undefined,
  pnl: false,
  price: null,
  symbol: 'symbol',
  timestamp: undefined,
  value: undefined,
});

const { amount, asset, price: knownPrice, timestamp, value: providedValue, loading: loadingProp } = toRefs(props);

// Composables
const { loading: calculationLoading, value: calculatedValue } = useAssetValue({
  amount: computed<BigNumber>(() => get(amount) ?? Zero),
  asset,
  knownPrice,
  timestamp,
});
const { assetOracle, isManualPrice } = useOracleInfo({
  isAssetPrice: computed<boolean>(() => true),
  priceAsset: asset,
});
const { currency } = useAmountDisplaySettings();

// Computed - symbol display
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

// Computed - value resolution
const hasProvidedValue = computed<boolean>(() => {
  const val = get(providedValue);
  return val !== undefined && val.gt(0);
});

const displayValue = computed<BigNumber>(() =>
  get(hasProvidedValue) ? get(providedValue)! : get(calculatedValue),
);

const loading = computed<boolean>(() =>
  get(hasProvidedValue) ? false : get(calculationLoading),
);

const showManualIndicator = computed<boolean>(() =>
  !isDefined(timestamp) && get(isManualPrice),
);

// Scrambling (depends on displayValue computed)
const { scrambledValue } = useScrambledValue({ value: displayValue });
</script>

<template>
  <div class="inline-flex items-baseline">
    <ManualPriceIndicator v-if="showManualIndicator" />
    <AmountDisplayBase
      :value="scrambledValue"
      :symbol="displaySymbol"
      :loading="loading || loadingProp"
      :pnl="pnl"
      :format="format"
      v-bind="$attrs"
    >
      <template #tooltip>
        <OracleBadge
          v-if="assetOracle"
          :oracle="assetOracle"
        />
      </template>
    </AmountDisplayBase>
  </div>
</template>
