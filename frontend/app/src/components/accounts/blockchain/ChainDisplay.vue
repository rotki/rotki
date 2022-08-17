<template>
  <list-item :title="item.symbol" :subtitle="item.name">
    <template #icon>
      <asset-icon size="26px" :identifier="item.symbol" />
    </template>
  </list-item>
</template>
<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { defineComponent, PropType } from '@vue/composition-api';
import ListItem from '@/components/helper/ListItem.vue';

export default defineComponent({
  name: 'ChainDisplay',
  components: { ListItem },
  props: {
    item: {
      required: true,
      type: Object as PropType<{ symbol: Blockchain; name: string }>
    }
  }
});
</script>
