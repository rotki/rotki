<script setup lang="ts">
import { toCapitalCase } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import { getPublicProtocolImagePath } from '@/modules/common/file/file';

interface Props {
  size?: string;
  chain: string;
  tooltip?: boolean;
}

const { chain, size = '24px', tooltip = false } = defineProps<Props>();

function getImageUrl(evmChain: string): string {
  return getPublicProtocolImagePath(`${evmChain}.svg`);
}

const chainData = computed(() => ({
  image: getImageUrl(chain),
  label: toCapitalCase(chain),
}));
</script>

<template>
  <RuiTooltip
    :disabled="!tooltip"
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <AppImage
        :size="size"
        :src="chainData.image"
        :alt="chainData.label"
      />
    </template>
    {{ chainData.label }}
  </RuiTooltip>
</template>
