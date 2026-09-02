<script setup lang="ts">
/**
 * Displays a raw asset amount with its symbol, as in `1.5 ETH`.
 *
 * @remarks
 * Not a fiat value: for that, reach for `AssetValueDisplay`. Values are scrambled for privacy
 * when the setting is on, and omitting `asset` renders the amount with no symbol.
 *
 * @example
 * ```vue
 * <AssetAmountDisplay asset="ETH" :amount="bigNumberify(1.5)" />
 * <AssetAmountDisplay asset="ETH" :amount="balance" no-collection-parent />
 * ```
 */
import type { BigNumber } from '@rotki/common';
import { useScrambledValue } from '@/modules/assets/amount-display';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
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
  /** Fixed number of decimal places to render, overriding the user's floating-precision setting */
  decimals?: number;
}

defineOptions({
  inheritAttrs: false,
});

const { amount, asset = '', decimals, noCollectionParent, noScramble } = defineProps<Props>();

const { useAssetInfo } = useAssetInfoRetrieval();
const resolutionOptions = computed(() => ({ collectionParent: !noCollectionParent }));
const info = useAssetInfo(() => asset, resolutionOptions);
const { scrambledValue } = useScrambledValue({ value: () => amount, noScramble: () => noScramble });

const assetSymbol = computed<string>(() => {
  if (!asset)
    return '';
  const assetInfoVal = get(info);
  return assetInfoVal?.symbol ?? asset;
});
</script>

<template>
  <AmountDisplayBase
    :value="scrambledValue"
    :symbol="assetSymbol"
    :loading="loading"
    :format="{ decimals, rounding: 'amount' }"
    :no-truncate="noTruncate"
    v-bind="$attrs"
  />
</template>
