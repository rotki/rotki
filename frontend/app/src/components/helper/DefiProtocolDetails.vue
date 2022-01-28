<template>
  <span v-bind="$attrs" class="d-flex flex-row align-center">
    <v-img
      width="26px"
      contain
      position="left"
      max-height="24px"
      :src="item.icon"
    />
    <span class="ml-1">{{ item.name }}</span>
  </span>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';

type Item = { icon: string; name: string };

export default defineComponent({
  name: 'DefiProtocolDetails',
  props: {
    item: { required: true, type: Object as PropType<Item> }
  }
});
</script>
