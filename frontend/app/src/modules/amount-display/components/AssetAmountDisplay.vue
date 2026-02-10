<script setup lang="ts">
/**
 * AssetAmountDisplay - Display a raw asset amount with its symbol.
 *
 * Shows the amount of an asset (e.g., "1.5 ETH"). NOT a fiat value.
 * Values are scrambled for privacy when enabled in settings.
 * If asset is not provided, displays just the raw value without a symbol.
 *
 * @example
 * <AssetAmountDisplay asset="ETH" :amount="bigNumberify(1.5)" />
 *
 * @example
 * <AssetAmountDisplay asset="BTC" :amount="balance" />
 *
 * @example
 * <AssetAmountDisplay asset="ETH" :amount="balance" no-collection-parent />
 *
 * @example
 * <AssetAmountDisplay :asset="optionalAsset" :amount="balance" />
 */
import type { BigNumber } from '@rotki/common';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useScrambledValue } from '@/modules/amount-display';
import AmountDisplayBase from './AmountDisplayBase.vue';

interface Props {
  /** Asset identifier (e.g., 'ETH', 'BTC'). If empty, displays value without symbol. */
  asset?: string;
  /** Amount of the asset */
  amount: BigNumber;
  /** Loading state */
  loading?: boolean;
  /** Disable collection parent resolution for symbol lookup */
  noCollectionParent?: boolean;
  /** Disable truncation on currency symbol */
  noTruncate?: boolean;
  /** Skip scrambling even when privacy mode is enabled */
  noScramble?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<Props>(), {
  asset: '',
  loading: false,
  noCollectionParent: false,
  noTruncate: false,
});

const { amount, asset, noCollectionParent, noScramble } = toRefs(props);

// Composables
const { assetInfo } = useAssetInfoRetrieval();
const resolutionOptions = computed(() => ({ collectionParent: !get(noCollectionParent) }));
const info = assetInfo(asset, resolutionOptions);
const { scrambledValue } = useScrambledValue({ value: amount, noScramble });

// Computed - returns empty string if no asset provided
const assetSymbol = computed<string>(() => {
  const assetVal = get(asset);
  if (!assetVal)
    return '';
  const assetInfoVal = get(info);
  return assetInfoVal?.symbol ?? assetVal;
});
</script>

<template>
  <AmountDisplayBase
    :value="scrambledValue"
    :symbol="assetSymbol"
    :loading="loading"
    :format="{ rounding: 'amount' }"
    :no-truncate="noTruncate"
    v-bind="$attrs"
  />
</template>
