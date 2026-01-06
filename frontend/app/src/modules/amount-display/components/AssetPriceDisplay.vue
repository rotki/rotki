<script setup lang="ts">
/**
 * AssetPriceDisplay - Display the price of an asset in user's currency.
 *
 * Shows the price per unit of an asset. NOT scrambled (prices are public data).
 *
 * @example
 * <AssetPriceDisplay asset="ETH" />
 *
 * @example
 * <AssetPriceDisplay asset="ETH" :price="knownPrice" />
 *
 * @example
 * <AssetPriceDisplay asset="ETH" :timestamp="1704067200" />
 */
import type { FormatOptions, SymbolDisplay, Timestamp } from '@/modules/amount-display/types';
import { type BigNumber, One } from '@rotki/common';
import { useAmountDisplaySettings, useAssetValue, useOracleInfo } from '@/modules/amount-display';
import AmountDisplayBase from './AmountDisplayBase.vue';
import ManualPriceIndicator from './ManualPriceIndicator.vue';
import OracleBadge from './OracleBadge.vue';

interface Props {
  /** Asset identifier (e.g., 'ETH', 'BTC') */
  asset: string;
  /** Known price (optional, will lookup if not provided) */
  price?: BigNumber | null;
  /** Timestamp for historic price lookup */
  timestamp?: Timestamp;
  /** Format options */
  format?: FormatOptions;
  /** Loading state */
  loading?: boolean;
  /** How to display the currency: 'symbol' (default, e.g. €), 'ticker' (e.g. EUR), or 'none' */
  symbol?: SymbolDisplay;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<Props>(), {
  format: undefined,
  price: null,
  symbol: 'symbol',
  timestamp: undefined,
});

const { asset, price: knownPrice, timestamp, loading: loadingProp } = toRefs(props);

// Get price for 1 unit of the asset
const { loading, value: priceValue } = useAssetValue({
  amount: One,
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
</script>

<template>
  <div class="inline-flex items-baseline">
    <ManualPriceIndicator v-if="isManualPrice" />
    <AmountDisplayBase
      :value="priceValue"
      :symbol="displaySymbol"
      :loading="loading || loadingProp"
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
