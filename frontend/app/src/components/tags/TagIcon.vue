<script setup lang="ts">
import { type Tag } from '@/types/tags';

withDefaults(
  defineProps<{
    tag: Tag;
    small?: boolean;
  }>(),
  {
    small: false
  }
);
</script>

<template>
  <VChip
    class="tag font-medium"
    label
    :small="small"
    :color="`#${tag.backgroundColor}`"
    :text-color="`#${tag.foregroundColor}`"
  >
    <AppImage
      v-if="tag.icon"
      class="mr-2"
      :width="1.25"
      :height="1.25"
      :src="tag.icon"
    />
    {{ tag.name }}
  </VChip>
</template>
