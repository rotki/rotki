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
    <VImg
      v-if="tag.icon"
      class="mr-2"
      :width="20"
      :height="20"
      :src="tag.icon"
    />
    <span>{{ tag.name }}</span>
  </VChip>
</template>
