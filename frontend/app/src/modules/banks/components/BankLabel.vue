<script setup lang="ts">
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

/** A bank as one line: the shared bank icon and its connector or institute name. */
const { connector, name } = defineProps<{
  connector: string;
  name: string;
}>();
</script>

<template>
  <span
    class="flex items-center gap-2 min-w-0"
    :title="connector"
  >
    <LocationIcon
      item="banks"
      icon
      size="20px"
    />
    <span class="truncate">{{ name }}</span>
  </span>
</template>
