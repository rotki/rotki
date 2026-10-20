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

const { t } = useI18n({ useScope: 'global' });

const menuOpened = ref<boolean>(false);
const menuContentRef = useTemplateRef<InstanceType<typeof AssetDetailsMenuContent>>('menuContentRef');

const { isPending } = useAssetInfoCache();
const shouldShowAmount = useSetting('shouldShowAmount');
const loading = isPending(() => asset.identifier);

const dense = computed<boolean>(() => display?.dense ?? false);
const inline = computed<boolean>(() => display?.inline ?? false);
const iconOnly = computed<boolean>(() => display?.iconOnly ?? false);
const size = computed<string>(() => display?.size ?? '30px');
const optimizeForVirtualScroll = computed<boolean>(() => display?.optimizeForVirtualScroll ?? false);

const hideMenu = computed<boolean>(() => actions?.hideMenu ?? false);
const hideActions = computed<boolean>(() => actions?.hideActions ?? false);

const enableAssociation = computed<boolean>(() => resolution?.enableAssociation ?? true);
const isCollectionParent = computed<boolean>(() => resolution?.isCollectionParent ?? false);
const forceChain = computed<string | undefined>(() => resolution?.forceChain);

const showChain = computed<boolean>(() => !get(isCollectionParent));

/** An asset rotki has no symbol for shows its identifier, so its row is never only an icon. */
const title = computed<string>(() => (asset.isCustomAsset ? asset.name : asset.symbol) || asset.identifier);

/** Left out when it only repeats the title, as for ETH, whose name is its symbol. */
const subtitle = computed<string>(() => {
  const text = (asset.isCustomAsset ? asset.customAssetType : asset.name) ?? '';
  return text.toLowerCase() === get(title).toLowerCase() ? '' : text;
});

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
      :size="size"
      :identifier="asset.identifier"
      :resolution-options="{ associate: enableAssociation }"
      :show-chain="showChain"
      :force-chain="forceChain"
      :optimize-for-virtual-scroll="optimizeForVirtualScroll"
    />
  </DefineImage>
  <ReuseImage
    v-if="hideMenu && iconOnly"
    v-bind="$attrs"
  />
  <ListItem
    v-else-if="hideMenu"
    no-padding
    no-hover
    class="max-w-80"
    :class="inline ? 'py-0.5' : 'py-2'"
    v-bind="$attrs"
    :size="dense ? 'sm' : 'md'"
    :inline="inline"
    :loading="loading"
    :blur-content="!shouldShowAmount"
    :title="title"
    :subtitle="subtitle"
  >
    <template #avatar>
      <ReuseImage />
    </template>
  </ListItem>
  <RuiMenu
    v-else
    :key="asset.identifier"
    v-model="menuOpened"
    class="flex min-w-0"
    :class-names="{ menu: 'w-64 max-w-[90%]' }"
    :options="{ placement: 'bottom-start' }"
  >
    <template #activator="{ attrs }">
      <ReuseImage
        v-if="iconOnly"
        v-bind="{ ...$attrs, ...useContextMenu(attrs) }"
      />
      <div
        v-else
        class="w-max max-w-full min-w-0 flex items-center gap-1 cursor-pointer group"
      >
        <ListItem
          no-padding
          no-hover
          class="max-w-80"
          :class="inline ? 'py-0.5' : 'py-2'"
          v-bind="{ ...$attrs, ...useContextMenu(attrs) }"
          :size="dense ? 'sm' : 'md'"
          :inline="inline"
          :loading="loading"
          :blur-content="!shouldShowAmount"
          :title="title"
          :subtitle="subtitle"
        >
          <template #avatar>
            <ReuseImage />
          </template>
        </ListItem>

        <RuiButton
          variant="text"
          icon
          size="sm"
          class="shrink-0 text-rui-text-secondary! transition-opacity opacity-0 group-hover:opacity-100 [tr:hover_&]:opacity-100 focus-visible:opacity-100 motion-reduce:transition-none"
          :class="{ 'opacity-100': menuOpened }"
          :aria-label="t('common.actions.more')"
          v-bind="attrs"
          @click.stop="openMenuHandler($event)"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            :size="16"
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
