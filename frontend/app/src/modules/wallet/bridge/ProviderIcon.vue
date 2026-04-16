<script setup lang="ts">
interface Props {
  metadata?: {
    icon: string;
    name: string;
  };
  size?: string;
}

const {
  metadata,
  size = '16px',
} = defineProps<Props>();
</script>

<template>
  <img
    v-if="metadata"
    :src="metadata.icon"
    :alt="metadata.name"
    :style="{ width: size, height: size }"
  />
</template>
