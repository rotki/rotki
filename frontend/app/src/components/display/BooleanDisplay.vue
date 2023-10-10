<script setup lang="ts">
withDefaults(
  defineProps<{
    display: boolean;
  }>(),
  {
    display: false
  }
);
</script>

<template>
  <RuiIcon
    :color="display ? 'success' : 'primary'"
    size="20"
    :name="display ? 'checkbox-circle-line' : 'close-circle-line'"
  />
</template>
