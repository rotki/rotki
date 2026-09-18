<script setup lang="ts">
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import { PoolType } from './types';

const { assets, type } = defineProps<{
  assets: string[];
  type: PoolType;
}>();

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
      <RuiMenu v-else>
        <template #activator>
          <div class="z-0 -ml-2 cursor-pointer rounded-full w-7 h-7 bg-rui-grey-300 dark:bg-rui-grey-700 text-rui-text text-xs flex items-center justify-center font-bold">
            +{{ assets.length - 1 }}
          </div>
        </template>
        <div class="p-2 flex">
          <AssetIcon
            v-for="asset in assets"
            :key="asset"
            circle
            :identifier="asset"
            size="32px"
            padding="0"
            :show-chain="false"
            hide-protocol
          />
        </div>
      </RuiMenu>
    </div>
    <div class="absolute -bottom-0.5 -right-1 p-px w-4 h-4 rounded-full bg-white dark:bg-rui-grey-900 ring-1 ring-black/[0.12] dark:ring-white/[0.12]">
      <AppImage
        size="0.875rem"
        :src="icon"
      />
    </div>
  </div>
</template>
