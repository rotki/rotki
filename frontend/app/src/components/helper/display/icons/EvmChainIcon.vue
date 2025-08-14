<script setup lang="ts">
import { toCapitalCase } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';

interface Props {
  size?: string;
  chain: string;
  tooltip?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: '24px',
  tooltip: false,
});

const { chain } = toRefs(props);

function getImageUrl(evmChain: string): string {
  return `./assets/images/protocols/${evmChain}.svg`;
}

const chainData = computed(() => {
  const chainProp = get(chain);

  return {
    image: getImageUrl(chainProp),
    label: toCapitalCase(chainProp),
  };
});
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
