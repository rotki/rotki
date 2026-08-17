<script setup lang="ts">
import type { NftAsset } from '@/modules/assets/nfts';
import type { AssetActions, AssetDisplay, AssetResolution } from '@/modules/assets/types';
import { omit } from 'es-toolkit';
import { useTemplateRef } from 'vue';
import AssetDetailsMenuContent from '@/modules/assets/AssetDetailsMenuContent.vue';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useAssetPageNavigation } from '@/modules/assets/use-asset-page-navigation';
import { useSetting } from '@/modules/settings/use-setting';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';

defineOptions({
  inheritAttrs: false,
});

const {
  actions,
  asset,
  display,
  resolution,
} = defineProps<{
  asset: NftAsset;
  display?: AssetDisplay;
  actions?: AssetActions;
  resolution?: AssetResolution;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const menuOpened = ref<boolean>(false);
const menuContentRef = useTemplateRef<InstanceType<typeof AssetDetailsMenuContent>>('menuContentRef');

const { isPending } = useAssetInfoCache();
const shouldShowAmount = useSetting('shouldShowAmount');
const loading = isPending(() => asset.identifier);

// Every field is read with `??` rather than by spreading the bag over a defaults object: a caller
// forwarding an optional value gives a present key holding `undefined`, which a spread would use to
// clobber the default. `AssetDetails` forwards its own optional `size` exactly that way.
const dense = computed<boolean>(() => display?.dense ?? false);
const iconOnly = computed<boolean>(() => display?.iconOnly ?? false);
const size = computed<string>(() => display?.size ?? '30px');
const showChain = computed<boolean>(() => display?.showChain ?? true);
const optimizeForVirtualScroll = computed<boolean>(() => display?.optimizeForVirtualScroll ?? false);

const hideMenu = computed<boolean>(() => actions?.hideMenu ?? false);
const hideActions = computed<boolean>(() => actions?.hideActions ?? false);
const changeable = computed<boolean>(() => actions?.changeable ?? false);

const enableAssociation = computed<boolean>(() => resolution?.enableAssociation ?? true);
const isCollectionParent = computed<boolean>(() => resolution?.isCollectionParent ?? false);
const forceChain = computed<string | undefined>(() => resolution?.forceChain);

const { navigateToDetails } = useAssetPageNavigation(() => asset.identifier, () => get(isCollectionParent));

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
      if (!get(hideMenu)) {
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
      fit="contain"
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
    :blur-content="!shouldShowAmount"
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
          :blur-content="!shouldShowAmount"
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
