<script setup lang="ts">
import type { Tag } from '@/types/tags';

withDefaults(
  defineProps<{
    tag: Tag;
    small?: boolean;
    showDescription?: boolean;
  }>(),
  {
    small: false,
    showDescription: false,
  },
);
</script>

<template>
  <div class="flex items-center">
    <RuiChip
      class="tag font-medium [&>span]:flex shrink-0"
      tile
      :size="small ? 'sm' : 'md'"
      :bg-color="`#${tag.backgroundColor}`"
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
    </RuiChip>
    <span
      v-if="showDescription"
      class="ml-4 text-sm leading-4 py-2 text-rui-text-secondary"
    >
      {{ tag.description }}
    </span>
  </div>
</template>
