<script setup lang="ts">
import type { TradableAsset } from '@/types/trade';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { isEvmNativeToken } from '@/types/asset';

const props = defineProps<{
  data: TradableAsset;
  list?: boolean;
}>();

const { t } = useI18n();

const { assetName, assetSymbol } = useAssetInfoRetrieval();
const { getChainName, getEvmChainName } = useSupportedChains();

const symbol = assetSymbol(props.data.asset, { collectionParent: false });

const name = computed(() => {
  const asset = props.data.asset;
  const name = get(assetName(asset, { collectionParent: false }));
  const isNative = isEvmNativeToken(asset);

  if (isNative) {
    const chain = props.data.chain;
    const chainName = get(getChainName(chain));
    return `${name} (in ${chainName} chain)`;
  }
  return name;
});
</script>

<template>
  <div class="flex gap-2 items-center">
    <AssetIcon
      size="32px"
      :identifier="data.asset"
      :force-chain="getEvmChainName(data.chain) || undefined"
      :resolution-options="{
        collectionParent: false,
      }"
    />
    <div
      class="truncate gap-4"
      :class="{
        'w-full flex items-center justify-between': list,
      }"
    >
      <div class="font-medium text-sm -mb-0.5 overflow-hidden truncate">
        <div class="truncate">
          {{ name }}
        </div>
        <div
          v-if="list"
          class="truncate text-rui-text-secondary font-normal"
        >
          {{ symbol }}
        </div>
      </div>
      <div
        v-if="data.price && data.fiatValue"
        class="text-xs text-rui-text-secondary flex gap-1 whitespace-nowrap"
        :class="{
          '!text-sm !text-rui-text': list,
        }"
      >
        <span v-if="!list">{{ t('trade.select_asset.balance') }}:</span>
        <div>
          <AmountDisplay :value="data.amount" />
        </div>
        <div>
          (<AmountDisplay
            force-currency
            show-currency="symbol"
            :value="data.fiatValue"
          />)
        </div>
      </div>
    </div>
  </div>
</template>
