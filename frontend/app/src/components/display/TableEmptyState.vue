<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';

defineProps<{
  text: string;
}>();

const { isDark } = useRotkiTheme();
</script>

<template>
  <div class="flex flex-col items-center text-center text-rui-text-secondary py-8">
    <AppImage
      :src="isDark ? '/assets/images/placeholder/table_no_data_placeholder_dark.svg' : '/assets/images/placeholder/table_no_data_placeholder.svg'"
      :alt="text"
      class="h-32"
    />
    {{ text }}
  </div>
</template>
