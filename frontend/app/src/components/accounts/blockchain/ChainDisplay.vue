<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

const props = withDefaults(
  defineProps<{
    chain: Blockchain;
    dense?: boolean;
    fullWidth?: boolean;
  }>(),
  {
    dense: false,
    fullWidth: true
  }
);

const { chain } = toRefs(props);

const { getChainName } = useSupportedChains();
const name = getChainName(chain);
</script>

<template>
  <ListItem :dense="dense" :title="name" :full-width="fullWidth">
    <template #icon>
      <AssetIcon size="26px" :identifier="chain" :show-chain="false" />
    </template>
  </ListItem>
</template>
