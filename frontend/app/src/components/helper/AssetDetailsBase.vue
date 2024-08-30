<script setup lang="ts">
import type { StyleValue } from 'vue';
import type { NftAsset } from '@/types/nfts';

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
    opensDetails: false,
    changeable: false,
    hideName: false,
    dense: false,
    enableAssociation: true,
    showChain: true,
    isCollectionParent: false,
  },
);

const { asset, opensDetails, isCollectionParent } = toRefs(props);

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
        size="26px"
        :src="asset.imageUrl"
      />
      <AssetIcon
        v-else
        :changeable="changeable"
        size="26px"
        :styled="assetStyled"
        :identifier="asset.identifier"
        :resolution-options="{ associate: enableAssociation }"
        :show-chain="showChain"
      />
    </template>
  </ListItem>
</template>
