<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import type { AssetActions, AssetDisplay, AssetIdentifierResolution } from '@/modules/assets/types';
import AssetDetailsBase from '@/modules/assets/AssetDetailsBase.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';

const {
  actions,
  asset,
  display,
  resolution,
} = defineProps<{
  asset: string;
  display?: AssetDisplay;
  actions?: AssetActions;
  resolution?: AssetIdentifierResolution;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { useAssetInfo } = useAssetInfoRetrieval();

const assetDetails = useAssetInfo(() => asset, computed<AssetResolutionOptions>(() => ({
  associate: resolution?.enableAssociation ?? true,
  collectionParent: resolution?.isCollectionParent ?? false,
  ...resolution?.options,
})));

const currentAsset = computed<AssetInfoWithId>(() => ({
  ...get(assetDetails),
  identifier: asset,
}));
</script>

<template>
  <!-- All three bags are forwarded by reference. Rebuilding them here would give the defaults a
       second home to drift in, and would hand the child a fresh object identity every render. Only
       `resolution.options` stops here, consumed by `useAssetInfo` above. -->
  <AssetDetailsBase
    :asset="currentAsset"
    :display="display"
    :actions="actions"
    :resolution="resolution"
    @refresh="emit('refresh')"
  />
</template>
