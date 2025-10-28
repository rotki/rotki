<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import { useLocations } from '@/composables/locations';
import { useRefMap } from '@/composables/utils/useRefMap';

const props = withDefaults(
  defineProps<{
    exchange: string;
    size?: string;
  }>(),
  { size: '1.5rem' },
);

const { exchange } = toRefs(props);
const { locationData } = useLocations();

const location = locationData(exchange);
const name = useRefMap(location, location => location?.name);
const image = useRefMap(location, location => location?.image ?? undefined);
</script>

<template>
  <div class="flex flex-row gap-2 items-center shrink">
    <AppImage
      class="icon-bg"
      :width="size"
      :height="size"
      contain
      :src="image"
    />
    <div v-text="name" />
  </div>
</template>
