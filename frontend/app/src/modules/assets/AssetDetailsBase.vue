<script setup lang="ts">
import type { NftAsset } from '@/modules/assets/nfts';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import AssetDetailsMenuContent from '@/modules/assets/AssetDetailsMenuContent.vue';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useAssetPageNavigation } from '@/modules/assets/use-asset-page-navigation';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';

defineOptions({
  inheritAttrs: false,
});

const {
  asset,
  changeable,
  dense,
  enableAssociation = true,
  forceChain,
  hideActions,
  hideMenu = false,
  iconOnly,
  isCollectionParent = false,
  optimizeForVirtualScroll,
  showChain = true,
  size = '30px',
} = defineProps<{
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
  optimizeForVirtualScroll?: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const menuOpened = ref<boolean>(false);
const menuContentRef = useTemplateRef<InstanceType<typeof AssetDetailsMenuContent>>('menuContentRef');

const { isPending } = useAssetInfoCache();
const { navigateToDetails } = useAssetPageNavigation(() => asset.identifier, () => isCollectionParent);
const loading = isPending(() => asset.identifier);

const [DefineImage, ReuseImage] = createReusableTemplate();

function openMenuHandler(event: MouseEvent) {
  event.preventDefault();
  event.stopPropagation();
  set(menuOpened, !get(menuOpened));
}

function useContextMenu(attrs: Record<string, unknown>) {
  return {
    ...omit(attrs, ['onClick']),
    onClick: () => {
      if (!hideMenu) {
        navigateToDetails();
      }
    },
    oncontextmenu: openMenuHandler,
  };
}

watch(menuOpened, (menuOpened) => {
  if (!menuOpened) {
    get(menuContentRef)?.setConfirm(false);
  }
});
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
      :optimize-for-virtual-scroll="optimizeForVirtualScroll"
    />
  </DefineImage>
  <!-- Skip RuiMenu entirely when hideMenu=true to avoid popper overhead in virtualized lists -->
  <ReuseImage
    v-if="hideMenu && iconOnly"
    v-bind="$attrs"
  />
  <ListItem
    v-else-if="hideMenu"
    no-padding
    no-hover
    class="max-w-[20rem]"
    v-bind="$attrs"
    :size="dense ? 'sm' : 'md'"
    :loading="loading"
    :title="asset.isCustomAsset ? asset.name : asset.symbol"
    :subtitle="asset.isCustomAsset ? asset.customAssetType : asset.name"
  >
    <template #avatar>
      <ReuseImage />
    </template>
  </ListItem>
  <RuiMenu
    v-else
    :key="asset.identifier"
    v-model="menuOpened"
    class="flex"
    menu-class="w-[16rem] max-w-[90%]"
    :popper="{ placement: 'bottom-start' }"
  >
    <template #activator="{ attrs }">
      <ReuseImage
        v-if="iconOnly"
        v-bind="{ ...$attrs, ...useContextMenu(attrs) }"
      />
      <div
        v-else
        class="w-max flex items-center gap-3 cursor-pointer hover:bg-rui-grey-300 dark:hover:bg-rui-grey-800 rounded-md group -ml-1 pl-1"
      >
        <ListItem
          no-padding
          no-hover
          class="max-w-[20rem]"
          v-bind="{ ...$attrs, ...useContextMenu(attrs) }"
          :size="dense ? 'sm' : 'md'"
          :loading="loading"
          :title="asset.isCustomAsset ? asset.name : asset.symbol"
          :subtitle="asset.isCustomAsset ? asset.customAssetType : asset.name"
        >
          <template #avatar>
            <ReuseImage />
          </template>
        </ListItem>

        <RuiButton
          variant="text"
          icon
          class="opacity-0 group-hover:opacity-100 mr-2 !p-2"
          v-bind="attrs"
          @click.stop="openMenuHandler($event)"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            size="20"
          />
        </RuiButton>
      </div>
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
