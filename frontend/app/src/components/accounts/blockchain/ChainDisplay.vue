<template>
  <list-item :title="item.symbol" :subtitle="item.name">
    <template #icon>
      <asset-icon size="26px" :identifier="item.symbol" />
    </template>
  </list-item>
</template>
<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import ListItem from '@/components/helper/ListItem.vue';

defineProps({
  item: {
    required: true,
    type: Object as PropType<{ symbol: Blockchain; name: string }>
  }
});
</script>
