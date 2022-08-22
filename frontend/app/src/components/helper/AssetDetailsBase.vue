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
        :styled="assetStyled"
        :identifier="identifier"
        :symbol="symbol"
      />
    </template>
  </list-item>
</template>

<script lang="ts">
import { Nullable } from '@rotki/common';
import { SupportedAsset } from '@rotki/common/lib/data';
import { get } from '@vueuse/core';
import { computed, defineComponent, PropType, toRefs } from 'vue';
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
      type: Object as PropType<
        | SupportedAsset
        | {
            identifier: string;
            symbol?: Nullable<string>;
            name?: Nullable<string>;
          }
      >
    },
    assetStyled: { required: false, type: Object, default: () => null },
    opensDetails: { required: false, type: Boolean, default: false },
    changeable: { required: false, type: Boolean, default: false },
    hideName: { required: false, type: Boolean, default: false },
    dense: { required: false, type: Boolean, default: false },
    enableAssociation: { required: false, type: Boolean, default: true }
  },
  setup(props) {
    const { asset, opensDetails, enableAssociation } = toRefs(props);
    const { assetSymbol, assetName } = useAssetInfoRetrieval();

    const identifier = computed(() => {
      const supportedAsset = get(asset);
      if ('ethereumAddress' in supportedAsset) {
        return `_ceth_${supportedAsset.ethereumAddress}`;
      }
      return supportedAsset.identifier;
    });
    const symbol = computed(() =>
      get(assetSymbol(get(identifier), get(enableAssociation)))
    );
    const name = computed(() =>
      get(assetName(get(identifier), get(enableAssociation)))
    );
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
