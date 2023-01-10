<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import ListItem from '@/components/helper/ListItem.vue';

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

const { getChainInfoById } = useSupportedChains();
const name = computed(() => {
  const chainVal = get(chain);
  return get(getChainInfoById(chainVal))?.name || chainVal;
});
</script>
<template>
  <list-item :dense="dense" :title="chain" :subtitle="dense ? '' : name">
    <template #icon>
      <asset-icon size="26px" :identifier="chain" :show-chain="false" />
    </template>
  </list-item>
</template>
