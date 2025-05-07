<script setup lang="ts">
import type { TradableAsset } from '@/modules/onchain/types';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';

const props = defineProps<{
  data: TradableAsset;
  list?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { assetName, assetSymbol } = useAssetInfoRetrieval();
const { getEvmChainName } = useSupportedChains();

const symbol = assetSymbol(props.data.asset, { collectionParent: false });
const name = assetName(props.data.asset, { collectionParent: false });
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
          {{ symbol }}
        </div>
        <div
          v-if="list || !(data.price && data.fiatValue)"
          class="truncate text-rui-text-secondary font-normal"
        >
          {{ name }}
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
