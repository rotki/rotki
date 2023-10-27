<script setup lang="ts">
interface Item {
  icon: string;
  name: string;
}

defineProps<{ item: Item }>();
</script>

<template>
  <span v-bind="$attrs" class="flex flex-row items-center">
    <VImg
      width="26px"
      contain
      position="left"
      max-height="24px"
      :src="item.icon"
    />
    <span class="ml-1">{{ item.name }}</span>
  </span>
</template>
