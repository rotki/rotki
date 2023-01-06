<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import ListItem from '@/components/helper/ListItem.vue';

withDefaults(
  defineProps<{
    item: { symbol: Blockchain; name: string };
    dense?: boolean;
  }>(),
  {
    dense: false
  }
);
</script>
<template>
  <list-item
    :dense="dense"
    :title="item.symbol"
    :subtitle="dense ? '' : item.name"
  >
    <template #icon>
      <asset-icon size="26px" :identifier="item.symbol" />
    </template>
  </list-item>
</template>
