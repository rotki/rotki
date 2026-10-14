<script setup lang="ts">
import { useLocations } from '@/modules/core/common/use-locations';
import IconMark from '@/modules/shell/components/IconMark.vue';

const { exchange, size = '1.5rem' } = defineProps<{
  exchange: string;
  size?: string;
}>();

const { useLocationData } = useLocations();

const location = useLocationData(() => exchange);
</script>

<template>
  <div class="flex gap-2 items-center shrink">
    <IconMark
      :size="size"
      :src="location?.image ?? undefined"
    />
    <div v-text="location?.name" />
  </div>
</template>
