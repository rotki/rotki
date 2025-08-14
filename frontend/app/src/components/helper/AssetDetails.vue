<script setup lang="ts">
import type { AssetInfoWithId } from '@/types/asset';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';

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
  }>(),
  {
    dense: false,
    enableAssociation: true,
    hideActions: false,
    isCollectionParent: false,
  },
);

const emit = defineEmits<{
  refresh: [];
}>();

const { asset } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();

const assetDetails = assetInfo(asset, computed(() => ({
  associated: props.enableAssociation,
  collectionParent: props.isCollectionParent,
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
    @refresh="emit('refresh')"
  />
</template>
