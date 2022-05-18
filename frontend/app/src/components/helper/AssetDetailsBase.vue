<template>
  <list-item
    v-bind="$attrs"
    :class="opensDetails ? 'asset-details-base--link' : null"
    :dense="dense"
    :title="symbol"
    :subtitle="name"
    @click="navigate"
  >
    <template #icon>
      <asset-icon
        :changeable="changeable"
        size="26px"
        :identifier="identifier"
        :symbol="symbol"
      />
    </template>
  </list-item>
</template>

<script lang="ts">
import { SupportedAsset } from '@rotki/common/lib/data';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import ListItem from '@/components/helper/ListItem.vue';
import { useRouter } from '@/composables/common';
import { Routes } from '@/router/routes';
import { useAssetInfoRetrieval } from '@/store/assets';

const AssetDetailsBase = defineComponent({
  name: 'AssetDetailsBase',
  components: { ListItem, AssetIcon },
  props: {
    asset: {
      required: true,
      type: Object as PropType<SupportedAsset>
    },
    opensDetails: { required: false, type: Boolean, default: false },
    changeable: { required: false, type: Boolean, default: false },
    hideName: { required: false, type: Boolean, default: false },
    dense: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { asset, opensDetails } = toRefs(props);
    const { assetSymbol, assetName } = useAssetInfoRetrieval();

    const identifier = computed(() => {
      const supportedAsset = get(asset);
      if ('ethereumAddress' in supportedAsset) {
        return `_ceth_${supportedAsset.ethereumAddress}`;
      }
      return supportedAsset.identifier;
    });
    const symbol = computed(() => get(assetSymbol(get(identifier))));
    const name = computed(() => get(assetName(get(identifier))));
    const router = useRouter();
    const navigate = () => {
      if (!get(opensDetails)) {
        return;
      }
      const id = get(identifier) ?? get(symbol);
      router.push({
        path: Routes.ASSETS.route.replace(':identifier', id)
      });
    };

    return {
      symbol,
      name,
      identifier,
      navigate
    };
  }
});
export default AssetDetailsBase;
</script>

<style scoped lang="scss">
.asset-details-base {
  &--link {
    cursor: pointer;
  }
}
</style>
