<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { LOOPRING_CHAIN } from '@/modules/onchain/blockchain-types';

interface Props {
  size?: string;
  chain: string;
}

const { chain, size = '26px' } = defineProps<Props>();

const { matchChain, useChainImageUrl } = useSupportedChains();

const src = useChainImageUrl(() => chain);

const OTHER_CHAINS = [
  LOOPRING_CHAIN,
];
</script>

<template>
  <AppImage
    v-if="matchChain(chain) || OTHER_CHAINS.includes(chain)"
    :key="src"
    :src="src"
    :width="size"
    :max-width="size"
    :height="size"
    :max-height="size"
    contain
    class="icon-bg"
  />
  <RuiIcon
    v-else
    :size="size"
    name="lu-link"
    class="text-rui-grey-400 dark:text-rui-grey-600 icon-bg"
  />
</template>
