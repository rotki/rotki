<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';

const props = withDefaults(
  defineProps<{
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
  }>(),
  {
    dense: false,
    enableAssociation: true,
    hideActions: false,
    isCollectionParent: false,
    optimizeForVirtualScroll: false,
  },
);

const emit = defineEmits<{
  refresh: [];
}>();

const { asset, resolutionOptions } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();

const assetDetails = assetInfo(asset, computed(() => ({
  associate: props.enableAssociation,
  collectionParent: props.isCollectionParent,
  ...get(resolutionOptions),
})));

const currentAsset = computed<AssetInfoWithId>(() => ({
  ...get(assetDetails),
  identifier: get(asset),
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
