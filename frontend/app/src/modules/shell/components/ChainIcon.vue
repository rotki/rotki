<script setup lang="ts">
import { LOOPRING_CHAIN } from '@/modules/balances/blockchain-types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';
import IconMark from '@/modules/shell/components/IconMark.vue';

interface Props {
  size?: string;
  chain: string;
}

const { chain, size = '26px' } = defineProps<Props>();

const { matchChain, useChainImageUrl } = useSupportedChains();
const shouldShowAmount = useSetting('shouldShowAmount');

const src = useChainImageUrl(() => chain);

const OTHER_CHAINS = [
  LOOPRING_CHAIN,
];
</script>

<template>
  <IconMark
    v-if="matchChain(chain) || OTHER_CHAINS.includes(chain)"
    :key="src"
    :src="src"
    :size="size"
    :class="{ blur: !shouldShowAmount }"
  />
  <RuiIcon
    v-else
    :size="size"
    name="lu-link"
    class="text-rui-grey-400 dark:text-rui-grey-600"
    :class="{ blur: !shouldShowAmount }"
  />
</template>
