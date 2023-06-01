<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

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

const { getChainName } = useSupportedChains();
const name = getChainName(chain);
</script>

<template>
  <list-item :dense="dense" :title="name">
    <template #icon>
      <asset-icon size="26px" :identifier="chain" :show-chain="false" />
    </template>
  </list-item>
</template>
