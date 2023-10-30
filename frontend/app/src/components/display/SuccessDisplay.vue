<script setup lang="ts">
withDefaults(
  defineProps<{
    success?: boolean;
    size?: string | number;
  }>(),
  {
    success: false,
    size: 20
  }
);
</script>

<template>
  <RuiIcon
    :color="success ? 'success' : 'primary'"
    :size="size"
    :name="success ? 'checkbox-circle-line' : 'close-circle-line'"
  />
</template>
