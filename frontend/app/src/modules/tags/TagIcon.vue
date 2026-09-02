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
    <RuiChip
      class="font-medium !rounded-md shrink-0"
      data-testid="tag"
      tile
      :class-names="{ content: 'flex font-mono' }"
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
