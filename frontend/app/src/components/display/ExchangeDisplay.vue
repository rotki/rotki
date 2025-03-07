<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
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
    <AdaptiveWrapper>
      <AppImage
        :width="size"
        :height="size"
        contain
        :src="image"
      />
    </AdaptiveWrapper>
    <div v-text="name" />
  </div>
</template>
