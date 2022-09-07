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

    const currentAsset = computed(() => {
      const details = get(assetInfo(get(asset), get(enableAssociation)));

      return {
        symbol: details ? details.symbol : get(asset),
        name: details ? details.name : get(asset),
        identifier: details ? details.identifier : get(asset)
      };
    });

    return {
      currentAsset
    };
  }
});
</script>
