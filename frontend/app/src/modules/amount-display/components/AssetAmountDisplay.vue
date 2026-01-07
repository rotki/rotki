<script setup lang="ts">
/**
 * AssetAmountDisplay - Display a raw asset amount with its symbol.
 *
 * Shows the amount of an asset (e.g., "1.5 ETH"). NOT a fiat value.
 * Values are scrambled for privacy when enabled in settings.
 *
 * @example
 * <AssetAmountDisplay asset="ETH" :amount="bigNumberify(1.5)" />
 *
 * @example
 * <AssetAmountDisplay asset="BTC" :amount="balance" />
 *
 * @example
 * <AssetAmountDisplay asset="ETH" :amount="balance" no-collection-parent />
 */
import type { BigNumber } from '@rotki/common';
import type { FormatOptions } from '@/modules/amount-display/types';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useScrambledValue } from '@/modules/amount-display';
import AmountDisplayBase from './AmountDisplayBase.vue';

interface Props {
  /** Asset identifier (e.g., 'ETH', 'BTC') */
  asset: string;
  /** Amount of the asset */
  amount: BigNumber;
  /** Format options */
  format?: FormatOptions;
  /** Apply PnL coloring (green positive, red negative) */
  pnl?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Disable collection parent resolution for symbol lookup */
  noCollectionParent?: boolean;
  /** Disable truncation on currency symbol */
  noTruncate?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<Props>(), {
  format: undefined,
  loading: false,
  noCollectionParent: false,
  noTruncate: false,
  pnl: false,
});

const { amount, asset, noCollectionParent } = toRefs(props);

// Composables
const { assetInfo } = useAssetInfoRetrieval();
const resolutionOptions = computed(() => ({ collectionParent: !get(noCollectionParent) }));
const info = assetInfo(asset, resolutionOptions);
const { scrambledValue } = useScrambledValue({ value: amount });

// Computed
const assetSymbol = computed<string>(() => {
  const assetInfoVal = get(info);
  return assetInfoVal?.symbol ?? get(asset);
});
</script>

<template>
  <AmountDisplayBase
    :value="scrambledValue"
    :symbol="assetSymbol"
    :loading="loading"
    :pnl="pnl"
    :format="{ ...format, rounding: 'amount' }"
    :no-truncate="noTruncate"
    v-bind="$attrs"
  />
</template>
