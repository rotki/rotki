<script setup lang="ts">
import type { Tag } from '@/types/tags';

defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    tag: Tag;
    small?: boolean;
    showDescription?: boolean;
  }>(),
  {
    showDescription: false,
    small: false,
  },
);
</script>

<template>
  <div class="flex items-center overflow-hidden">
    <RuiChip
      class="font-medium !rounded-md shrink-0"
      data-cy="tag"
      tile
      content-class="flex font-mono"
      :size="small ? 'sm' : 'md'"
      :bg-color="`#${tag.backgroundColor}`"
      :text-color="`#${tag.foregroundColor}`"
      v-bind="$attrs"
    >
      {{ tag.name }}
    </RuiChip>
    <div
      v-if="showDescription"
      class="ml-4 text-sm leading-4 py-2 text-rui-text-secondary overflow-hidden whitespace-normal"
    >
      {{ tag.description }}
    </div>
  </div>
</template>
