<script setup lang="ts">
import { computed } from 'vue';

const { iso, title = '' } = defineProps<{
  iso: string;
  title?: string;
}>();

const flagIconClass = computed<string>(() =>
  `fi-${iso.toLowerCase()}`,
);
</script>

<template>
  <span
    v-if="iso"
    class="fi text-base rounded-xs"
    :class="flagIconClass"
    :title="title || iso"
  />
</template>
