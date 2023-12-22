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
  <ListItem :size="dense ? 'sm' : 'md'" :title="name" no-padding no-hover>
    <template #avatar>
      <ChainIcon :chain="chain" />
    </template>
  </ListItem>
</template>
