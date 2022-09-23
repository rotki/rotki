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
        :identifier="asset.identifier"
        :symbol="symbol"
        :name="name"
      />
    </template>
  </list-item>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import ListItem from '@/components/helper/ListItem.vue';
import { useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';
import { AssetInfoWithId } from '@/types/assets';

const props = defineProps({
  asset: {
    required: true,
    type: Object as PropType<AssetInfoWithId>
  },
  assetStyled: { required: false, type: Object, default: () => null },
  opensDetails: { required: false, type: Boolean, default: false },
  changeable: { required: false, type: Boolean, default: false },
  hideName: { required: false, type: Boolean, default: false },
  dense: { required: false, type: Boolean, default: false }
});

const { asset, opensDetails } = toRefs(props);

const symbol = computed(() => get(asset).symbol ?? '');
const name = computed(() => get(asset).name ?? '');

const router = useRouter();
const navigate = async () => {
  if (!get(opensDetails)) {
    return;
  }
  const id = encodeURIComponent(get(asset).identifier);
  await router.push({
    path: Routes.ASSETS.route.replace(':identifier', id)
  });
};
</script>

<style scoped lang="scss">
.asset-details-base {
  &--link {
    cursor: pointer;
  }
}
</style>
