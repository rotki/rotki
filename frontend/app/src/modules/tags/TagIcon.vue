<script setup lang="ts">
import type { Tag } from '@/modules/tags/tags';
import { useSetting } from '@/modules/settings/use-setting';

defineOptions({
  inheritAttrs: false,
});

const { tag, small = false, showDescription = false } = defineProps<{
  tag: Tag;
  small?: boolean;
  showDescription?: boolean;
}>();

const shouldShowAmount = useSetting('shouldShowAmount');
</script>

<template>
  <div
    class="flex items-center overflow-hidden"
    :class="{ blur: !shouldShowAmount }"
  >
    <!-- a small pill in the body font; the colours stay the user's -->
    <RuiChip
      class="font-medium shrink-0"
      :class="{ 'h-5! px-2! text-xs!': small }"
      data-testid="tag"
      :class-names="{ content: 'flex' }"
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
