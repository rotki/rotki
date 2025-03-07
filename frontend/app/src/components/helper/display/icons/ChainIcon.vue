<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { useSupportedChains } from '@/composables/info/chains';

interface Props {
  size?: string;
  chain: string;
}

const props = withDefaults(defineProps<Props>(), {
  size: '26px',
});

const { chain } = toRefs(props);

const { getChainImageUrl } = useSupportedChains();

const src = getChainImageUrl(chain);
</script>

<template>
  <AdaptiveWrapper>
    <AppImage
      :src="src"
      :width="size"
      :max-width="size"
      :height="size"
      :max-height="size"
      contain
    />
  </AdaptiveWrapper>
</template>
