<script setup lang="ts">
import type { NftAsset } from '@/types/nfts';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import AppImage from '@/components/common/AppImage.vue';
import ListItem from '@/components/common/ListItem.vue';
import AssetDetailsMenuContent from '@/components/helper/AssetDetailsMenuContent.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetPageNavigation } from '@/composables/assets/navigation';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useAssetCacheStore } from '@/store/assets/asset-cache';

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

const emit = defineEmits<{
  refresh: [];
}>();

const { asset, hideMenu, isCollectionParent } = toRefs(props);

const symbol = useRefMap(asset, asset => asset.symbol ?? '');
const name = useRefMap(asset, asset => asset.name ?? '');

const { isPending } = useAssetCacheStore();
const identifier = useRefMap(asset, asset => asset.identifier);
const loading = computed<boolean>(() => get(isPending(identifier)));

const [DefineImage, ReuseImage] = createReusableTemplate();
const menuContentRef = useTemplateRef<InstanceType<typeof AssetDetailsMenuContent>>('menuContentRef');

const { navigateToDetails } = useAssetPageNavigation(identifier, isCollectionParent);

function updateMenuVisibility(value: boolean) {
  if (!value) {
    get(menuContentRef)?.setConfirm(false);
  }
}

function useContextMenu(attrs: Record<string, any>) {
  return {
    ...omit(attrs, ['onClick']),
    onClick: () => {
      if (!get(hideMenu)) {
        navigateToDetails();
      }
    },
    oncontextmenu: (event: MouseEvent) => {
      event.preventDefault();
      attrs.onClick(event);
    },
  };
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
      :force-chain="forceChain"
    />
  </DefineImage>
  <RuiMenu
    :key="identifier"
    class="flex"
    :disabled="hideMenu"
    menu-class="w-[16rem] max-w-[90%]"
    :open-delay="400"
    :popper="{ placement: 'bottom-start' }"
    @update:model-value="updateMenuVisibility($event)"
  >
    <template #activator="{ attrs }">
      <ReuseImage
        v-if="iconOnly"
        v-bind="{ ...$attrs, ...useContextMenu(attrs) }"
      />
      <ListItem
        v-else
        no-padding
        no-hover
        class="max-w-[20rem] cursor-pointer"
        v-bind="{ ...$attrs, ...useContextMenu(attrs) }"
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
      @refresh="emit('refresh')"
    />
  </RuiMenu>
</template>
