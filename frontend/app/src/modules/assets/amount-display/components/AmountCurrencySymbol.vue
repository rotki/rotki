<script setup lang="ts">
defineProps<{
  symbol: string;
  noTruncate?: boolean;
}>();
</script>

<template>
  <span
    data-testid="display-currency"
    :class="noTruncate ? '' : 'truncate max-w-20'"
  >
    {{ symbol }}
  </span>
</template>
