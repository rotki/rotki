<script setup lang="ts">
import type { TradableAsset } from '@/modules/onchain/types';
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';

const props = defineProps<{
  data: TradableAsset;
  list?: boolean;
  amount?: BigNumber;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { assetName, assetSymbol } = useAssetInfoRetrieval();
const { getEvmChainName } = useSupportedChains();

const symbol = assetSymbol(props.data.asset, { collectionParent: false });
const name = assetName(props.data.asset, { collectionParent: false });
</script>

<template>
  <div class="flex gap-2 items-center">
    <AssetDetails
      icon-only
      size="32px"
      :asset="data.asset"
      hide-actions
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
        v-if="!list && data.price"
        class="text-sm text-rui-text flex items-center gap-1 whitespace-nowrap"
      >
        <span>{{ t('trade.select_asset.balance') }}:</span>
        <RuiSkeletonLoader
          v-if="!amount"
          class="w-28 flex"
        />

        <template v-else>
          <div>
            <AmountDisplay :value="amount" />
          </div>
          <div>
            (<AmountDisplay
              force-currency
              show-currency="symbol"
              :value="data.price.multipliedBy(amount)"
            />)
          </div>
          <div>
            <RuiButton
              icon
              variant="text"
              size="sm"
              class="!p-1"
              @click.stop="emit('refresh')"
            >
              <RuiIcon
                name="lu-refresh-ccw"
                size="12"
              />
            </RuiButton>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
