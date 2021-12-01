<template>
  <list-item
    v-bind="$attrs"
    :class="opensDetails ? 'asset-details-base--link' : null"
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
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import ListItem from '@/components/helper/ListItem.vue';
import { useRouter } from '@/composables/common';
import { Routes } from '@/router/routes';

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
    hideName: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { asset, opensDetails } = toRefs(props);
    const identifier = computed(() => {
      const supportedAsset = asset.value;
      if ('ethereumAddress' in supportedAsset) {
        return `_ceth_${supportedAsset.ethereumAddress}`;
      }
      return supportedAsset.identifier;
    });
    const symbol = computed(() => asset.value.symbol);
    const name = computed(() => asset.value.name);
    const router = useRouter();
    const navigate = () => {
      if (!opensDetails.value) {
        return;
      }
      const id = identifier.value ?? symbol.value;
      router.push({
        path: Routes.ASSETS.replace(':identifier', id)
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
