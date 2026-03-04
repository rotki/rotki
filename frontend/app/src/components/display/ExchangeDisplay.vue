<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { useLocations } from '@/composables/locations';

const { exchange, size = '1.5rem' } = defineProps<{
  exchange: string;
  size?: string;
}>();

const { locationData } = useLocations();

const location = locationData(() => exchange);
</script>

<template>
  <div class="flex flex-row gap-2 items-center shrink">
    <AppImage
      class="icon-bg"
      :width="size"
      :height="size"
      contain
      :src="location?.image ?? undefined"
    />
    <div v-text="location?.name" />
  </div>
</template>
