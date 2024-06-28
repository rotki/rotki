<script setup lang="ts">
import { toSentenceCase } from '@/utils/text';

interface Item {
  icon: string;
  name: string;
}

withDefaults(
  defineProps<{
    item: Item;
    size?: string;
    loading?: boolean;
    vertical?: boolean;
  }>(),
  {
    size: '1.5rem',
    loading: false,
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
      :loading="loading"
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
