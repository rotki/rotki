<script setup>
const props = defineProps({
  iso: { type: String, default: null },
  title: { type: String, default: null },
  squared: { type: Boolean, default: true },
});

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
