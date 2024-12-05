<script setup lang="ts">
withDefaults(
  defineProps<{
    success?: boolean;
    size?: string | number;
  }>(),
  {
    size: 20,
    success: false,
  },
);
</script>

<template>
  <RuiIcon
    :color="success ? 'success' : 'primary'"
    :size="size"
    :name="success ? 'checkbox-circle-line' : 'close-circle-line'"
  />
</template>
