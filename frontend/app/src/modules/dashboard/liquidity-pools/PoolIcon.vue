<script setup lang="ts">
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import { PoolType } from './types';

const { assets, type } = defineProps<{
  assets: string[];
  type: PoolType;
}>();

const { t } = useI18n({ useScope: 'global' });

const data = [{
  icon: getPublicProtocolImagePath('uniswap.svg'),
  identifier: PoolType.UNISWAP_V2,
}, {
  icon: getPublicProtocolImagePath('sushiswap.svg'),
  identifier: PoolType.SUSHISWAP,
}] as const;

const icon = computed<string | undefined>(() => {
  const selected = data.find(({ identifier }) => identifier === type);

  if (!selected)
    return undefined;

  return selected.icon;
});

const multiple = computed<boolean>(() => assets.length > 2);

const moreLabel = computed<string>(() => t('modules.dashboard.liquidity_pools.pool_icon.more', { count: assets.length - 1 }));
</script>

<template>
  <div class="flex relative">
    <div class="flex items-center">
      <AssetIcon
        circle
        :identifier="assets[0]"
        size="28px"
        padding="0"
        :show-chain="false"
        hide-protocol
      />
      <AssetIcon
        v-if="!multiple"
        circle
        class="z-0 -ml-2"
        :identifier="assets[1]"
        size="28px"
        padding="0"
        :show-chain="false"
        hide-protocol
      />
      <RuiMenu
        v-else
        lazy
        role="dialog"
        :menu-label="moreLabel"
        :class-names="{ menu: 'min-w-48 max-w-72' }"
      >
        <template #activator="{ attrs }">
          <button
            type="button"
            class="z-0 -ml-2 cursor-pointer rounded-full w-7 h-7 bg-rui-grey-300 dark:bg-rui-grey-700 text-rui-text text-xs flex items-center justify-center font-bold focus-visible:focus-ring"
            data-testid="pool-icon-more"
            :aria-label="moreLabel"
            v-bind="attrs"
          >
            +{{ assets.length - 1 }}
          </button>
        </template>
        <ul
          class="py-1 px-3 flex flex-col"
          data-testid="pool-icon-assets"
        >
          <li
            v-for="asset in assets"
            :key="asset"
          >
            <AssetDetails
              :asset="asset"
              :display="{ dense: true, size: '24px' }"
              :actions="{ hideMenu: true }"
            />
          </li>
        </ul>
      </RuiMenu>
    </div>
    <div class="absolute -bottom-0.5 -right-1 p-px w-4 h-4 rounded-full bg-white dark:bg-rui-grey-900 ring-1 ring-black/12 dark:ring-white/12">
      <AppImage
        size="0.875rem"
        :src="icon"
      />
    </div>
  </div>
</template>
