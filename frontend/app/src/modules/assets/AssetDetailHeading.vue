<script setup lang="ts">
import type { AssetWithResolutionStatus } from '@/modules/assets/use-asset-info-retrieval';
import { computed } from 'vue';
import AssetExternalLinks from '@/modules/assets/AssetExternalLinks.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

interface HeadingContract {
  address: string;
  location?: string;
}

const { asset, contractInfo, isCustomAsset } = defineProps<{
  identifier: string;
  asset: AssetWithResolutionStatus | null | undefined;
  contractInfo: HeadingContract | undefined;
  isCustomAsset: boolean | undefined;
  isCollectionParent: boolean;
}>();

const { getChainName } = useSupportedChains();

const title = computed<string | undefined>(() => (isCustomAsset ? asset?.name : asset?.symbol) ?? undefined);

const subtitle = computed<string | undefined>(() => (isCustomAsset ? asset?.customAssetType : asset?.name) ?? undefined);

const chainName = computed<string | undefined>(() => {
  const location = contractInfo?.location;
  return location ? getChainName(location) : undefined;
});
</script>

<template>
  <div class="flex items-center gap-4 min-w-0">
    <AssetIcon
      :identifier="identifier"
      size="48px"
      :show-chain="!isCollectionParent"
    />

    <div class="flex flex-col min-w-0">
      <span class="text-h5 leading-7 font-semibold truncate">{{ title }}</span>
      <div
        class="flex flex-wrap items-center gap-x-2 h-6 text-sm text-rui-text-secondary"
        data-testid="asset-meta"
      >
        <span v-if="subtitle">{{ subtitle }}</span>
        <template v-if="contractInfo">
          <span
            v-if="subtitle"
            class="size-1 rounded-full bg-rui-text-disabled"
          />
          <span v-if="chainName">{{ chainName }}</span>
          <HashLink
            :location="contractInfo.location"
            type="token"
            :text="contractInfo.address"
            :display-mode="contractInfo.location ? 'default' : 'copy'"
            size="14"
          />
        </template>
        <template v-if="asset?.coingecko || asset?.cryptocompare">
          <span class="size-1 rounded-full bg-rui-text-disabled" />
          <AssetExternalLinks
            :coingecko="asset.coingecko"
            :cryptocompare="asset.cryptocompare"
          />
        </template>
      </div>
    </div>
  </div>
</template>
