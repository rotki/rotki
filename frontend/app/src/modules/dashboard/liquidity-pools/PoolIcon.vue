<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { getPublicProtocolImagePath } from '@/utils/file';
import { PoolType } from './types';

const props = defineProps<{
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
  const selected = data.find(({ identifier }) => identifier === props.type);

  if (!selected)
    return undefined;

  return selected.icon;
});

const multiple = computed<boolean>(() => props.assets.length > 2);
</script>

<template>
  <div class="flex relative">
    <div class="flex items-center">
      <AssetIcon
        circle
        :identifier="assets[0]"
        size="32px"
        padding="0"
        :show-chain="false"
      />
      <AssetIcon
        v-if="!multiple"
        circle
        :class="$style['second-icon']"
        :identifier="assets[1]"
        size="32px"
        padding="0"
        :show-chain="false"
      />
      <RuiMenu v-else>
        <template #activator>
          <div :class="[$style['second-icon'], $style['more-assets']]">
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
          />
        </div>
      </RuiMenu>
    </div>
    <div :class="$style['lp-type-icon']">
      <AppImage
        size="1rem"
        :src="icon"
      />
    </div>
  </div>
</template>

<style module lang="scss">
.second-icon {
  @apply z-0 -ml-2.5;
}

.more-assets {
  @apply cursor-pointer rounded-full w-8 h-8 bg-rui-grey-300 text-rui-text flex items-center justify-center font-bold;
}

.lp-type-icon {
  @apply relative p-0.5 w-5 h-5 rounded-full bg-rui-grey-200 -ml-3 -mt-3;
}

:global(.dark) {
  .more-assets {
    @apply bg-rui-grey-700;
  }
}
</style>
