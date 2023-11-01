<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type StyleValue } from 'vue/types/jsx';
import { Routes } from '@/router/routes';
import { type NftAsset } from '@/types/nfts';

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
    isCollectionParent: false
  }
);

const { asset, opensDetails, isCollectionParent } = toRefs(props);
const rootAttrs = useAttrs();

const symbol: ComputedRef<string> = computed(() => get(asset).symbol ?? '');
const name: ComputedRef<string> = computed(() => get(asset).name ?? '');

const router = useRouter();
const navigate = async () => {
  if (!get(opensDetails)) {
    return;
  }
  const id = encodeURIComponent(get(asset).identifier);
  const collectionParent = get(isCollectionParent);

  await router.push({
    path: Routes.ASSETS.replace(':identifier', id),
    query: !collectionParent
      ? {}
      : {
          collectionParent: 'true'
        }
  });
};

const { isPending } = useAssetCacheStore();
const loading: ComputedRef<boolean> = computed(() =>
  get(isPending(get(asset).identifier))
);
</script>

<template>
  <ListItem
    v-bind="rootAttrs"
    :class="opensDetails ? 'cursor-pointer' : null"
    :dense="dense"
    :loading="loading"
    :title="asset.isCustomAsset ? name : symbol"
    :subtitle="asset.isCustomAsset ? asset.customAssetType : name"
    @click="navigate()"
  >
    <template #icon>
      <VImg
        v-if="asset.imageUrl"
        contain
        height="26px"
        width="26px"
        max-width="26px"
        :src="asset.imageUrl"
      />
      <AssetIcon
        v-else
        :changeable="changeable"
        size="26px"
        :styled="assetStyled"
        :identifier="asset.identifier"
        :enable-association="enableAssociation"
        :show-chain="showChain"
      />
    </template>
  </ListItem>
</template>
