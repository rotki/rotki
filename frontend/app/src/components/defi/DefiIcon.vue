<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { toSentenceCase } from '@rotki/common';

interface Item {
  icon?: string;
  name: string;
}

defineOptions({
  inheritAttrs: false,
});

withDefaults(
  defineProps<{
    item: Item;
    size?: string;
    vertical?: boolean;
  }>(),
  {
    size: '1.5rem',
    vertical: false,
  },
);
</script>

<template>
  <div
    v-bind="$attrs"
    class="flex items-center"
    :class="vertical ? 'flex-col gap-1' : 'flex-row gap-2'"
  >
    <AppImage
      class="icon-bg"
      :src="item.icon"
      :size="size"
      :loading="!item.icon"
      contain
    />
    <div
      class="text-rui-text-secondary"
      :class="{ '-mb-1 text-center': vertical }"
    >
      {{ toSentenceCase(item.name) }}
    </div>
  </div>
</template>
