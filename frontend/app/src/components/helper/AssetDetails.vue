<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type AssetInfoWithId } from '@/types/asset';
import { getAddressFromEvmIdentifier } from '@/utils/assets';

const props = withDefaults(
  defineProps<{
    asset: string;
    assetStyled?: Record<string, unknown>;
    opensDetails?: boolean;
    hideName?: boolean;
    dense?: boolean;
    enableAssociation?: boolean;
    isCollectionParent?: boolean;
    link?: boolean;
  }>(),
  {
    assetStyled: undefined,
    opensDetails: false,
    hideName: false,
    dense: false,
    enableAssociation: true,
    isCollectionParent: false,
    link: false
  }
);

const { asset, enableAssociation, isCollectionParent } = toRefs(props);
const { assetInfo } = useAssetInfoRetrieval();

const assetDetails = assetInfo(asset, enableAssociation, isCollectionParent);
const address = reactify(getAddressFromEvmIdentifier)(asset);

const currentAsset: ComputedRef<AssetInfoWithId> = computed(() => ({
  ...get(assetDetails),
  identifier: get(asset)
}));
</script>

<template>
  <div class="flex-row d-flex">
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
      type="address"
      :evm-chain="assetDetails?.evmChain"
      link-only
      :text="address"
    />
  </div>
</template>
