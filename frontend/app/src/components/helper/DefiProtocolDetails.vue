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
<script setup lang="ts">
import { PropType } from 'vue';

type Item = { icon: string; name: string };

defineProps({
  item: { required: true, type: Object as PropType<Item> }
});
</script>
