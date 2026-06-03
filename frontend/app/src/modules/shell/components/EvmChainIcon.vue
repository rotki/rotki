<script setup lang="ts">
import { toCapitalCase } from '@rotki/common';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import AppImage from '@/modules/shell/components/AppImage.vue';

interface Props {
  size?: string;
  chain: string;
  tooltip?: boolean;
}

const { chain, size = '24px', tooltip = false } = defineProps<Props>();

const { shouldShowAmount } = storeToRefs(useFrontendSettingsStore());

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
    :disabled="!tooltip || !shouldShowAmount"
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <AppImage
        :size="size"
        :src="chainData.image"
        :alt="chainData.label"
        :class="{ blur: !shouldShowAmount }"
      />
    </template>
    {{ chainData.label }}
  </RuiTooltip>
</template>
