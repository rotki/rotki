<script setup lang="ts">
interface Item {
  icon: string;
  name: string;
}

defineProps<{ item: Item }>();
</script>

<template>
  <div v-bind="$attrs" class="flex flex-row items-center gap-2">
    <AppImage class="icon-bg p-[0.1rem]" :src="item.icon" contain size="24px" />
    <div class="text-capitalize text-rui-text-secondary">{{ item.name }}</div>
  </div>
</template>
