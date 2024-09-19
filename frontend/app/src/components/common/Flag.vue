<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    iso: string;
    title?: string;
    squared?: boolean;
  }>(),
  {
    title: '',
    squared: true,
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
