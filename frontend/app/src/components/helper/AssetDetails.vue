<template>
  <div>
    <asset-details-base
      :hide-name="hideName"
      :asset="currentAsset"
      :opens-details="opensDetails"
      :dense="dense"
      :asset-styled="assetStyled"
      :enable-association="enableAssociation"
    />
  </div>
</template>

<script setup lang="ts">
import { ComputedRef } from 'vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { useNftAssetInfoStore } from '@/store/assets/nft';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { AssetInfoWithId } from '@/types/assets';

const props = defineProps({
  asset: {
    required: true,
    type: String,
    validator: (value: string): boolean => {
      return !!value && value.length > 0;
    }
  },
  assetStyled: { required: false, type: Object, default: () => null },
  opensDetails: { required: false, type: Boolean, default: false },
  hideName: { required: false, type: Boolean, default: false },
  dense: { required: false, type: Boolean, default: false },
  enableAssociation: { required: false, type: Boolean, default: true }
});

const { asset, enableAssociation } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();
const { getNftDetails } = useNftAssetInfoStore();

const assetDetails = assetInfo(asset, enableAssociation);
const nftDetails = getNftDetails(asset);

const currentAsset: ComputedRef<AssetInfoWithId> = computed(() => {
  const nftAsset = get(nftDetails);

  if (nftAsset) {
    return {
      symbol: nftAsset.symbol,
      name: nftAsset.name,
      identifier: get(asset)
    };
  }

  return {
    ...get(assetDetails),
    identifier: get(asset)
  };
});
</script>
