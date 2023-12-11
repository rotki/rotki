<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

interface Props {
  size?: string;
  chain: Blockchain;
}

const props = withDefaults(defineProps<Props>(), {
  size: '26px'
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
