<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    iso: string;
    title?: string;
    squared?: boolean;
  }>(),
  {
    squared: false,
    title: '',
  },
);

const flagIconClass = computed(() =>
  `fi-${props.iso.toLowerCase()} ${props.squared ? 'fis ' : ''}`,
);
</script>

<template>
  <span
    v-if="iso"
    class="fi"
    :class="flagIconClass"
    :title="title || iso"
  />
</template>
