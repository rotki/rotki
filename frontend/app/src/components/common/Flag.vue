<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    iso: string;
    title?: string;
  }>(),
  {
    title: '',
  },
);

const flagIconClass = computed(() =>
  `fi-${props.iso.toLowerCase()}`,
);
</script>

<template>
  <span
    v-if="iso"
    class="fi text-base rounded-sm"
    :class="flagIconClass"
    :title="title || iso"
  />
</template>
