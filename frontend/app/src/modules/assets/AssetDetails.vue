<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import type { AssetActions, AssetDisplay, AssetResolution } from '@/modules/assets/types';
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

// Computed rather than inline literals: an object built in the template is a new identity on every
// parent render, which would re-render the child even inside a virtualized table.
const baseDisplay = computed<AssetDisplay>(() => ({
  dense,
  iconOnly,
  optimizeForVirtualScroll,
  showChain: !isCollectionParent,
  size,
}));

const baseActions = computed<AssetActions>(() => ({
  hideActions,
  hideMenu,
}));

const baseResolution = computed<AssetResolution>(() => ({
  enableAssociation,
  forceChain,
  isCollectionParent,
}));
</script>

<template>
  <AssetDetailsBase
    :asset="currentAsset"
    :display="baseDisplay"
    :actions="baseActions"
    :resolution="baseResolution"
    @refresh="emit('refresh')"
  />
</template>
