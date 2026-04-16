<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import AppImage from '@/modules/shell/components/AppImage.vue';

const { exchange, size = '1.5rem' } = defineProps<{
  exchange: string;
  size?: string;
}>();

const { useLocationData } = useLocations();

const location = useLocationData(() => exchange);
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
