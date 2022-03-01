<template>
  <div>
    <asset-details-base
      :hide-name="hideName"
      :asset="currentAsset"
      :opens-details="opensDetails"
      :dense="dense"
    />
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { useAssetInfoRetrieval } from '@/store/assets';

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
    opensDetails: { required: false, type: Boolean, default: false },
    hideName: { required: false, type: Boolean, default: false },
    dense: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { asset } = toRefs(props);

    const { assetInfo } = useAssetInfoRetrieval();

    const currentAsset = computed(() => {
      const details = get(assetInfo(get(asset)));
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
