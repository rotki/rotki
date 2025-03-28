<script setup lang="ts">
import type { AssetInfoWithId } from '@/types/asset';
import type { StyleValue } from 'vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import HashLink from '@/modules/common/links/HashLink.vue';
import { getAddressFromEvmIdentifier } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    asset: string;
    assetStyled?: StyleValue;
    opensDetails?: boolean;
    hideName?: boolean;
    dense?: boolean;
    enableAssociation?: boolean;
    isCollectionParent?: boolean;
    link?: boolean;
  }>(),
  {
    assetStyled: undefined,
    dense: false,
    enableAssociation: true,
    hideName: false,
    isCollectionParent: false,
    link: false,
    opensDetails: false,
  },
);

const { asset } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();

const assetDetails = assetInfo(asset, computed(() => ({
  associated: props.enableAssociation,
  collectionParent: props.isCollectionParent,
})));
const address = reactify(getAddressFromEvmIdentifier)(asset);

const currentAsset = computed<AssetInfoWithId>(() => ({
  ...get(assetDetails),
  identifier: get(asset),
}));
</script>

<template>
  <div class="flex-row flex">
    <AssetDetailsBase
      :hide-name="hideName"
      :asset="currentAsset"
      :opens-details="opensDetails"
      :dense="dense"
      :asset-styled="assetStyled"
      :enable-association="enableAssociation"
      :show-chain="!isCollectionParent"
      :is-collection-parent="isCollectionParent"
    />
    <HashLink
      v-if="link && address"
      type="token"
      :location="assetDetails?.evmChain"
      display-mode="link"
      hide-text
      :text="address"
    />
  </div>
</template>
