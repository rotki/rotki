<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';

const props = withDefaults(
  defineProps<{
    chain: Blockchain;
    dense?: boolean;
  }>(),
  {
    dense: false
  }
);

const { chain } = toRefs(props);

const isEth2 = computed(() => get(chain) === Blockchain.ETH2);

const { getChainName } = useSupportedChains();
const name = getChainName(chain);
</script>

<template>
  <list-item
    :dense="dense"
    :title="isEth2 ? name : chain"
    :subtitle="dense ? '' : name"
  >
    <template #icon>
      <asset-icon size="26px" :identifier="chain" :show-chain="false" />
    </template>
  </list-item>
</template>
