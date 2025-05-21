<script setup lang="ts">
import type { NftAsset } from '@/types/nfts';
import AppImage from '@/components/common/AppImage.vue';
import ListItem from '@/components/common/ListItem.vue';
import AssetDetailsMenuContent from '@/components/helper/AssetDetailsMenuContent.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useTemplateRef } from 'vue';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    asset: NftAsset;
    changeable?: boolean;
    hideActions?: boolean;
    dense?: boolean;
    enableAssociation?: boolean;
    showChain?: boolean;
    isCollectionParent?: boolean;
    hideMenu?: boolean;
    iconOnly?: boolean;
    size?: string;
    forceChain?: string;
  }>(),
  {
    changeable: false,
    dense: false,
    enableAssociation: true,
    hideActions: false,
    hideMenu: false,
    iconOnly: false,
    isCollectionParent: false,
    showChain: true,
    size: '30px',
  },
);

const { asset } = toRefs(props);

const symbol = useRefMap(asset, asset => asset.symbol ?? '');
const name = useRefMap(asset, asset => asset.name ?? '');

const { isPending } = useAssetCacheStore();
const loading = computed<boolean>(() => get(isPending(get(asset).identifier)));

const [DefineImage, ReuseImage] = createReusableTemplate();
const menuContentRef = useTemplateRef<InstanceType<typeof AssetDetailsMenuContent>>('menuContentRef');

function updateMenuVisibility(value: boolean) {
  if (!value) {
    get(menuContentRef)?.setConfirm(false);
  }
}
</script>

<template>
  <DefineImage>
    <AppImage
      v-if="asset.imageUrl"
      contain
      :size="size"
      :src="asset.imageUrl"
    />
    <AssetIcon
      v-else
      :changeable="changeable"
      :size="size"
      :identifier="asset.identifier"
      :resolution-options="{ associate: enableAssociation }"
      :show-chain="showChain"
      :no-tooltip="!hideMenu"
      :force-chain="forceChain"
    />
  </DefineImage>
  <RuiMenu
    class="flex"
    :disabled="hideMenu"
    menu-class="w-[16rem] max-w-[90%]"
    :open-on-hover="iconOnly"
    :open-delay="400"
    :close-delay="iconOnly ? 200 : 0"
    :popper="{ placement: 'bottom-start' }"
    @update:model-value="updateMenuVisibility($event)"
  >
    <template #activator="{ attrs }">
      <ReuseImage
        v-if="iconOnly"
        v-bind="{ ...$attrs, ...attrs }"
      />
      <ListItem
        v-else
        no-padding
        no-hover
        class="max-w-[20rem] cursor-pointer"
        v-bind="{ ...$attrs, ...attrs }"
        :size="dense ? 'sm' : 'md'"
        :loading="loading"
        :title="asset.isCustomAsset ? name : symbol"
        :subtitle="asset.isCustomAsset ? asset.customAssetType : name"
      >
        <template #avatar>
          <ReuseImage />
        </template>
      </ListItem>
    </template>

    <AssetDetailsMenuContent
      ref="menuContentRef"
      :asset="asset"
      :icon-only="iconOnly"
      :hide-actions="hideActions"
      :is-collection-parent="isCollectionParent"
    />
  </RuiMenu>
</template>
