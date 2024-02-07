<script setup lang="ts">
interface Item {
  icon: string;
  name: string;
}

defineProps<{ item: Item }>();
</script>

<template>
  <div
    v-bind="$attrs"
    class="flex flex-row items-center gap-2"
  >
    <AppImage
      class="icon-bg"
      :src="item.icon"
      contain
      size="24px"
    />
    <div class="capitalize text-rui-text-secondary">
      {{ item.name }}
    </div>
  </div>
</template>
