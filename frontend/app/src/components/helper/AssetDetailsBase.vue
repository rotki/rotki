<script setup lang="ts">
import type { NftAsset } from '@/types/nfts';
import type { StyleValue } from 'vue';
import AppImage from '@/components/common/AppImage.vue';
import ListItem from '@/components/common/ListItem.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetCacheStore } from '@/store/assets/asset-cache';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    asset: NftAsset;
    assetStyled?: StyleValue;
    opensDetails?: boolean;
    changeable?: boolean;
    hideName?: boolean;
    dense?: boolean;
    enableAssociation?: boolean;
    showChain?: boolean;
    isCollectionParent?: boolean;
  }>(),
  {
    assetStyled: undefined,
    changeable: false,
    dense: false,
    enableAssociation: true,
    hideName: false,
    isCollectionParent: false,
    opensDetails: false,
    showChain: true,
  },
);

const { asset, isCollectionParent, opensDetails } = toRefs(props);

const symbol = computed<string>(() => get(asset).symbol ?? '');
const name = computed<string>(() => get(asset).name ?? '');

const router = useRouter();

async function navigate() {
  if (!get(opensDetails))
    return;
  const collectionParent = get(isCollectionParent);

  await router.push({
    name: '/assets/[identifier]',
    params: {
      identifier: get(asset).identifier,
    },
    ...(!collectionParent
      ? {}
      : {
          query: {
            collectionParent: 'true',
          },
        }),
  });
}

const { isPending } = useAssetCacheStore();
const loading = computed<boolean>(() => get(isPending(get(asset).identifier)));
</script>

<template>
  <ListItem
    no-padding
    no-hover
    class="max-w-[20rem]"
    v-bind="$attrs"
    :class="opensDetails ? 'cursor-pointer' : null"
    :size="dense ? 'sm' : 'md'"
    :loading="loading"
    :title="asset.isCustomAsset ? name : symbol"
    :subtitle="asset.isCustomAsset ? asset.customAssetType : name"
    @click="navigate()"
  >
    <template #avatar>
      <AppImage
        v-if="asset.imageUrl"
        contain
        size="30px"
        :src="asset.imageUrl"
      />
      <AssetIcon
        v-else
        :changeable="changeable"
        size="30px"
        :styled="assetStyled"
        :identifier="asset.identifier"
        :resolution-options="{ associate: enableAssociation }"
        :show-chain="showChain"
      />
    </template>
  </ListItem>
</template>
