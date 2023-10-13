<script setup lang="ts">
withDefaults(
  defineProps<{
    success: boolean;
  }>(),
  {
    success: false
  }
);
</script>

<template>
  <RuiIcon
    :color="success ? 'success' : 'primary'"
    size="20"
    :name="success ? 'checkbox-circle-line' : 'close-circle-line'"
  />
</template>
