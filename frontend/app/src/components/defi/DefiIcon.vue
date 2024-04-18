<script setup lang="ts">
interface Item {
  icon: string;
  name: string;
}

withDefaults(defineProps<{ item: Item; size?: string }>(), { size: '1.5rem' });
</script>

<template>
  <div
    v-bind="$attrs"
    class="flex flex-row items-center gap-2"
  >
    <AppImage
      class="icon-bg"
      :src="item.icon"
      :size="size"
      contain
    />
    <div class="capitalize text-rui-text-secondary">
      {{ item.name }}
    </div>
  </div>
</template>
