<template>
  <list-item
    v-bind="rootAttrs"
    :class="opensDetails ? 'asset-details-base--link' : null"
    :dense="dense"
    :title="asset.isCustomAsset ? name : symbol"
    :subtitle="asset.isCustomAsset ? asset.customAssetType : name"
    @click="navigate"
  >
    <template #icon>
      <v-img
        v-if="asset.imageUrl"
        contain
        height="26px"
        width="26px"
        max-width="26px"
        :src="asset.imageUrl"
      />
      <asset-icon
        v-else
        :changeable="changeable"
        size="26px"
        :styled="assetStyled"
        :identifier="asset.identifier"
        :enable-association="enableAssociation"
      />
    </template>
  </list-item>
</template>

<script setup lang="ts">
import { ComputedRef, PropType } from 'vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import ListItem from '@/components/helper/ListItem.vue';
import { useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';
import { NftAsset } from '@/store/assets/nft';

const props = defineProps({
  asset: {
    required: true,
    type: Object as PropType<NftAsset>
  },
  assetStyled: { required: false, type: Object, default: () => null },
  opensDetails: { required: false, type: Boolean, default: false },
  changeable: { required: false, type: Boolean, default: false },
  hideName: { required: false, type: Boolean, default: false },
  dense: { required: false, type: Boolean, default: false },
  enableAssociation: { required: false, type: Boolean, default: true }
});

const { asset, opensDetails } = toRefs(props);
const rootAttrs = useAttrs();

const symbol: ComputedRef<string> = computed(() => get(asset).symbol ?? '');
const name: ComputedRef<string> = computed(() => get(asset).name ?? '');

const router = useRouter();
const navigate = async () => {
  if (!get(opensDetails)) {
    return;
  }
  const id = encodeURIComponent(get(asset).identifier);
  await router.push({
    path: Routes.ASSETS.replace(':identifier', id)
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
