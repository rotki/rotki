<script setup lang="ts">
interface Item {
  icon: string;
  name: string;
}

defineProps<{ item: Item }>();
</script>

<template>
  <span v-bind="$attrs" class="flex flex-row items-center">
    <AppImage :src="item.icon" width="26px" contain max-height="24px" />
    <span class="ml-1">{{ item.name }}</span>
  </span>
</template>
