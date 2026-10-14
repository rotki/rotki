<script setup lang="ts">
import { toSentenceCase } from '@rotki/common';
import IconMark from '@/modules/shell/components/IconMark.vue';

interface Item {
  icon?: string;
  name: string;
}

defineOptions({
  inheritAttrs: false,
});

const { item, size = '1.5rem', vertical = false } = defineProps<{
  item: Item;
  size?: string;
  vertical?: boolean;
}>();
</script>

<template>
  <div
    v-bind="$attrs"
    class="flex items-center"
    :class="vertical ? 'flex-col gap-1' : 'flex-row gap-2'"
  >
    <IconMark
      :src="item.icon"
      :size="size"
      :loading="!item.icon"
    />
    <div
      class="text-rui-text-secondary"
      :class="{ '-mb-1 text-center': vertical }"
    >
      {{ toSentenceCase(item.name) }}
    </div>
  </div>
</template>
