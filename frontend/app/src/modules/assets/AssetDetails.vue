<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';

const {
  asset,
  dense,
  enableAssociation = true,
  forceChain,
  hideActions,
  hideMenu,
  iconOnly,
  isCollectionParent = false,
  optimizeForVirtualScroll,
  resolutionOptions,
  size,
} = defineProps<{
  asset: string;
  dense?: boolean;
  enableAssociation?: boolean;
  isCollectionParent?: boolean;
  hideMenu?: boolean;
  hideActions?: boolean;
  iconOnly?: boolean;
  size?: string;
  forceChain?: string;
  optimizeForVirtualScroll?: boolean;
  resolutionOptions?: AssetResolutionOptions;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { useAssetInfo } = useAssetInfoRetrieval();

const assetDetails = useAssetInfo(() => asset, computed<AssetResolutionOptions>(() => ({
  associate: enableAssociation,
  collectionParent: isCollectionParent,
  ...resolutionOptions,
})));

const currentAsset = computed<AssetInfoWithId>(() => ({
  ...get(assetDetails),
  identifier: asset,
}));
</script>

<template>
  <AssetDetailsBase
    :hide-menu="hideMenu"
    :hide-actions="hideActions"
    :icon-only="iconOnly"
    :asset="currentAsset"
    :dense="dense"
    :enable-association="enableAssociation"
    :show-chain="!isCollectionParent"
    :is-collection-parent="isCollectionParent"
    :size="size"
    :force-chain="forceChain"
    :optimize-for-virtual-scroll="optimizeForVirtualScroll"
    @refresh="emit('refresh')"
  />
</template>
