<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

const { color, icon, title, description } = defineProps<{
  color: 'info' | 'warning';
  icon: RuiIcons;
  title: string;
  description: string;
}>();
</script>

<template>
  <div class="fixed inset-0 bg-black/80 backdrop-blur-xs flex items-center justify-center p-4 z-50">
    <div class="bg-rui-grey-100 dark:bg-rui-grey-800 p-8 rounded-lg shadow-2xl max-w-md flex flex-col items-center text-center">
      <RuiIcon
        :name="icon"
        size="40"
        class="mb-4"
        :class="color === 'info' ? 'text-rui-info' : 'text-rui-warning'"
      />
      <h2 class="text-h5 font-medium mb-2 text-rui-text">
        {{ title }}
      </h2>
      <p class="text-rui-text-secondary">
        {{ description }}
      </p>
    </div>
  </div>
</template>
