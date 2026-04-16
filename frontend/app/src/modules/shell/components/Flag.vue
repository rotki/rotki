<script setup lang="ts">
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
    class="fi text-base rounded-sm"
    :class="flagIconClass"
    :title="title || iso"
  />
</template>
