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
    :name="success ? 'lu-circle-check' : 'lu-circle-x'"
  />
</template>
