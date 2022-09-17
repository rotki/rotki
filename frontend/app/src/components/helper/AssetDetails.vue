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

<script lang="ts">
import { get } from '@vueuse/core';
import { computed, defineComponent, toRefs } from 'vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { useNftAssetInfoStore } from '@/store/assets/nft';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';

export default defineComponent({
  name: 'AssetDetails',
  components: { AssetDetailsBase },
  props: {
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
  },
  setup(props) {
    const { asset, enableAssociation } = toRefs(props);

    const { assetInfo } = useAssetInfoRetrieval();
    const { getNftDetails } = useNftAssetInfoStore();

    const currentAsset = computed(() => {
      const id = get(asset);
      const info = getNftDetails(id) ?? assetInfo(id, get(enableAssociation));
      const details = get(info);

      return {
        symbol: details ? details.symbol : id,
        name: details ? details.name : id,
        identifier: details ? details.identifier : id
      };
    });

    return {
      currentAsset
    };
  }
});
</script>
