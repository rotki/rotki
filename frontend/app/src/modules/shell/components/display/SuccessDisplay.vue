<script setup lang="ts">
import { RuiIcon } from '@rotki/ui-library';

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
