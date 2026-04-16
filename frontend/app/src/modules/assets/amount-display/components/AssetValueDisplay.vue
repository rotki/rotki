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
import type { Timestamp } from '@/modules/assets/amount-display/types';
import { type BigNumber, Zero } from '@rotki/common';
import { useAmountDisplaySettings, useAssetValue, useOracleInfo, useScrambledValue } from '@/modules/assets/amount-display';
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
  /** Loading state */
  loading?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const {
  amount,
  asset,
  price: knownPrice,
  timestamp,
  value: providedValue,
  loading: loadingProp,
} = defineProps<Props>();

// Composables
const { loading: calculationLoading, value: calculatedValue } = useAssetValue({
  amount: computed<BigNumber>(() => amount ?? Zero),
  asset: () => asset,
  knownPrice: () => knownPrice,
  timestamp: () => timestamp,
});
const { assetOracle, isManualPrice } = useOracleInfo({
  isAssetPrice: computed<boolean>(() => true),
  priceAsset: () => asset,
});
const { currency } = useAmountDisplaySettings();

// Computed - currency symbol (always uses user's default)
const displaySymbol = computed<string>(() => get(currency).unicodeSymbol);

// Computed - value resolution
const hasProvidedValue = computed<boolean>(() => providedValue !== undefined && providedValue.gt(0));

const displayValue = computed<BigNumber>(() =>
  get(hasProvidedValue) ? providedValue! : get(calculatedValue),
);

const loading = computed<boolean>(() =>
  get(hasProvidedValue) ? false : get(calculationLoading),
);

const showManualIndicator = computed<boolean>(() =>
  !isDefined(timestamp) && get(isManualPrice),
);

const showAssetOracle = computed<boolean>(() =>
  !isDefined(timestamp) && isDefined(assetOracle),
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
      v-bind="$attrs"
    >
      <template
        v-if="showAssetOracle"
        #tooltip
      >
        <OracleBadge
          v-if="assetOracle"
          :oracle="assetOracle"
        />
      </template>
    </AmountDisplayBase>
  </div>
</template>
