<script setup lang="ts">
/**
 * AmountDisplay - Legacy component that delegates to specialized display components.
 *
 * @deprecated For new code, prefer using the specialized components directly:
 *
 * - **FiatDisplay** - Display fiat values with optional currency conversion
 *   ```vue
 *   <FiatDisplay :value="usdAmount" from="USD" />
 *   <FiatDisplay :value="amount" symbol="ticker" />
 *   ```
 *
 * - **AssetValueDisplay** - Display asset value (amount × price) in user's currency
 *   ```vue
 *   <AssetValueDisplay asset="ETH" :amount="balance" />
 *   <AssetValueDisplay asset="ETH" :amount="balance" :timestamp="{ ms: eventTimeMs }" />
 *   ```
 *
 * - **AssetPriceDisplay** - Display asset price (not scrambled)
 *   ```vue
 *   <AssetPriceDisplay asset="ETH" />
 *   <AssetPriceDisplay asset="ETH" :price="knownPrice" />
 *   ```
 *
 * - **AssetAmountDisplay** - Display raw asset amount with symbol
 *   ```vue
 *   <AssetAmountDisplay :amount="balance" asset="ETH" />
 *   ```
 */
import type { AssetResolutionOptions } from '@/composables/assets/retrieval';
import type { FormatOptions, Timestamp } from '@/modules/amount-display/types';
import type { ShownCurrency } from '@/types/currencies';
import { type BigNumber, One, Zero } from '@rotki/common';
import {
  AssetAmountDisplay,
  AssetPriceDisplay,
  AssetValueDisplay,
  FiatDisplay,
  ValueDisplay,
} from '@/modules/amount-display/components';

export interface AmountInputProps {
  value: BigNumber | undefined;
  loading?: boolean;
  amount?: BigNumber;
  // This is what the fiat currency is `value` in. If it is null, it means we want to show it the way it is, no conversion, e.g. amount of an asset.
  fiatCurrency?: string | null;
  showCurrency?: ShownCurrency;
  forceCurrency?: boolean;
  asset?: string;
  // This is price of `priceAsset`
  priceOfAsset?: BigNumber | null;
  // This is asset we want to calculate the value from, instead get it directly from `value`
  priceAsset?: string;
  integer?: boolean;
  assetPadding?: number;
  // This prop to give color to the text based on the value
  pnl?: boolean;
  isAssetPrice?: boolean;
  noTruncate?: boolean;
  timestamp?: number;
  // Whether the `timestamp` prop is presented with `milliseconds` value or not
  milliseconds?: boolean;
  /**
   * Amount display text is really large
   */
  xl?: boolean;
  resolutionOptions?: AssetResolutionOptions;
}

const props = withDefaults(
  defineProps<AmountInputProps>(),
  {
    amount: () => One,
    asset: '',
    assetPadding: 0,
    fiatCurrency: null,
    forceCurrency: false,
    integer: false,
    isAssetPrice: false,
    loading: false,
    milliseconds: false,
    noTruncate: false,
    pnl: false,
    priceAsset: '',
    priceOfAsset: null,
    resolutionOptions: () => ({}),
    showCurrency: 'none',
    timestamp: -1,
    xl: false,
  },
);

// Convert legacy timestamp/milliseconds props to Timestamp type
const timestampValue = computed<Timestamp | undefined>(() => {
  if (props.timestamp <= 0)
    return undefined;
  return props.milliseconds ? { ms: props.timestamp } : props.timestamp;
});

// Format options from integer prop
const formatOptions = computed<FormatOptions | undefined>(() =>
  props.integer ? { integer: true } : undefined,
);

// XL styling class
const xlClass = computed<string>(() =>
  props.xl ? 'text-[2rem] leading-[3rem] sm:text-[3rem] sm:leading-[4rem]' : '',
);

// Determine which display mode to use
const displayMode = computed<'price' | 'assetValue' | 'fiat' | 'assetAmount' | 'rawValue'>(() => {
  const hasPriceAsset = !!props.priceAsset;
  const hasSourceCurrency = isDefined(toRef(props, 'fiatCurrency'));
  const hasAsset = !!props.asset;
  const wantsCurrency = props.showCurrency !== 'none';

  // Mode 1: Asset price display (isAssetPrice flag with priceAsset)
  if (props.isAssetPrice && hasPriceAsset) {
    return 'price';
  }

  // Mode 2: Fiat display (value with source currency)
  // Converts value from source currency to user's currency
  // Takes priority over assetValue when fiatCurrency is set
  if (hasSourceCurrency) {
    return 'fiat';
  }

  // Mode 3: Asset value display (priceAsset set, no fiatCurrency)
  // Shows manual price indicator, uses provided value or calculates from amount × price
  if (hasPriceAsset) {
    return 'assetValue';
  }

  // Mode 4: Fiat display (wants currency symbol without fiatCurrency)
  if (wantsCurrency) {
    return 'fiat';
  }

  // Mode 4: Asset amount display (has asset for symbol lookup)
  if (hasAsset) {
    return 'assetAmount';
  }

  // Mode 5: Raw value display (no currency context, no asset)
  return 'rawValue';
});

// For fiat mode, determine the "from" currency (empty = no conversion)
const fiatFrom = computed<string>(() => {
  if (props.forceCurrency)
    return '';
  return props.fiatCurrency ?? '';
});

// Value with Zero fallback
const displayValue = computed<BigNumber>(() => props.value ?? Zero);

// Amount with One fallback
const displayAmount = computed<BigNumber>(() => props.amount ?? One);

// Map resolutionOptions.collectionParent to noCollectionParent
const noCollectionParent = computed<boolean>(() => props.resolutionOptions.collectionParent === false);

// Map showCurrency to FiatDisplay symbol prop
const fiatSymbol = computed<'symbol' | 'ticker' | 'none'>(() => {
  switch (props.showCurrency) {
    case 'none':
      return 'none';
    case 'ticker':
    case 'name':
      return 'ticker';
    case 'symbol':
    default:
      return 'symbol';
  }
});
</script>

<template>
  <!-- Mode 1: Asset Price Display -->
  <AssetPriceDisplay
    v-if="displayMode === 'price'"
    :asset="priceAsset"
    :price="priceOfAsset"
    :timestamp="timestampValue"
    :format="formatOptions"
    :class="xlClass"
    :loading="loading"
  />

  <!-- Mode 2: Asset Value Display (uses provided value or calculates amount × price) -->
  <AssetValueDisplay
    v-else-if="displayMode === 'assetValue'"
    :asset="priceAsset"
    :amount="displayAmount"
    :value="displayValue"
    :price="priceOfAsset"
    :timestamp="timestampValue"
    :loading="loading"
    :format="formatOptions"
    :pnl="pnl"
    :class="xlClass"
  />

  <!-- Mode 3: Fiat Display (converts value between currencies) -->
  <FiatDisplay
    v-else-if="displayMode === 'fiat'"
    :value="displayValue"
    :from="fiatFrom"
    :timestamp="timestampValue"
    :format="formatOptions"
    :pnl="pnl"
    :symbol="fiatSymbol"
    :class="xlClass"
    :loading="loading"
  />

  <!-- Mode 4: Asset Amount Display (shows amount with asset symbol) -->
  <AssetAmountDisplay
    v-else-if="displayMode === 'assetAmount'"
    :amount="displayValue"
    :asset="asset"
    :loading="loading"
    :pnl="pnl"
    :format="formatOptions"
    :no-collection-parent="noCollectionParent"
    :class="xlClass"
  />

  <!-- Mode 5: Raw Value Display (no symbol) -->
  <ValueDisplay
    v-else
    :value="displayValue"
    :loading="loading"
    :pnl="pnl"
    :format="formatOptions"
    :class="xlClass"
  />
</template>
