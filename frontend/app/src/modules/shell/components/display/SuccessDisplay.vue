<script setup lang="ts">
const { success = false, size = 20 } = defineProps<{
  success?: boolean;
  size?: string | number;
}>();
</script>

<template>
  <RuiIcon
    :color="success ? 'success' : 'primary'"
    :size="size"
    :name="success ? 'lu-circle-check' : 'lu-circle-x'"
  />
</template>
