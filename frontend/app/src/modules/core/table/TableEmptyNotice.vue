<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

defineProps<{
  icon: RuiIcons;
  title: string;
  description?: string;
}>();

defineSlots<{
  default?: () => any;
}>();
</script>

<template>
  <!-- in place of the generic "no data" picture: an icon that says why the table is empty, and what to do next -->
  <div
    class="flex flex-col items-center text-center py-10 px-4"
    data-testid="table-empty-notice"
  >
    <div class="size-12 rounded-full bg-rui-neutral-950/5 dark:bg-white/8 text-rui-text-secondary flex items-center justify-center mb-4">
      <RuiIcon
        :name="icon"
        size="24"
      />
    </div>
    <p class="text-base font-medium text-rui-text">
      {{ title }}
    </p>
    <p
      v-if="description"
      class="mt-1 max-w-sm text-sm text-rui-text-secondary whitespace-normal"
    >
      {{ description }}
    </p>
    <div
      v-if="$slots.default"
      class="mt-4 flex gap-2"
    >
      <slot />
    </div>
  </div>
</template>
