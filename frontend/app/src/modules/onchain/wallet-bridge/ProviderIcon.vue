<script setup lang="ts">
interface Props {
  metadata?: {
    icon: string;
    name: string;
  };
  size?: string;
}

withDefaults(defineProps<Props>(), {
  metadata: undefined,
  size: '16px',
});
</script>

<template>
  <img
    v-if="metadata"
    :src="metadata.icon"
    :alt="metadata.name"
    :style="{ width: size, height: size }"
  />
</template>
