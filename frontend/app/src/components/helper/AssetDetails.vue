<template>
  <div>
    <asset-details-base
      :hide-name="hideName"
      :asset="currentAsset"
      :opens-details="opensDetails"
    />
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { setupAssetInfoRetrieval } from '@/composables/balances';

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
    hideName: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { asset } = toRefs(props);

    const { getAssetInfo } = setupAssetInfoRetrieval();

    const currentAsset = computed(() => {
      const details = getAssetInfo(asset.value);
      return {
        symbol: details ? details.symbol : asset.value,
        name: details ? details.name : asset.value,
        identifier: details ? details.identifier : asset.value
      };
    });

    return {
      currentAsset
    };
  }
});
</script>
