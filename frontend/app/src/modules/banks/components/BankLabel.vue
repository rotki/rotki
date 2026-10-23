<script setup lang="ts">
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

/** A bank as one line: its icon, then the name its manifest gives it rather than the bare location. */
const { location, name } = defineProps<{
  location: string;
  name: string;
}>();
</script>

<template>
  <span class="flex items-center gap-2 min-w-0">
    <LocationIcon
      :item="location"
      icon
      size="20px"
    />
    <span class="truncate">{{ name }}</span>
  </span>
</template>
