<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type AssetInfoWithId } from '@/types/asset';

const props = defineProps({
  asset: {
    required: true,
    type: String,
    validator: (value: string): boolean => !!value && value.length > 0
  },
  assetStyled: { required: false, type: Object, default: () => null },
  opensDetails: { required: false, type: Boolean, default: false },
  hideName: { required: false, type: Boolean, default: false },
  dense: { required: false, type: Boolean, default: false },
  enableAssociation: { required: false, type: Boolean, default: true },
  isCollectionParent: { required: false, type: Boolean, default: false }
});

const { asset, enableAssociation, isCollectionParent } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();

const assetDetails = assetInfo(asset, enableAssociation, isCollectionParent);

const currentAsset: ComputedRef<AssetInfoWithId> = computed(() => ({
  ...get(assetDetails),
  identifier: get(asset)
}));
</script>

<template>
  <div>
    <asset-details-base
      :hide-name="hideName"
      :asset="currentAsset"
      :opens-details="opensDetails"
      :dense="dense"
      :asset-styled="assetStyled"
      :enable-association="enableAssociation"
      :show-chain="!isCollectionParent"
      :is-collection-parent="isCollectionParent"
    />
  </div>
</template>
