<script setup lang="ts">
defineProps<{
  symbol: string;
  noTruncate?: boolean;
}>();
</script>

<template>
  <span
    data-cy="display-currency"
    :class="noTruncate ? '' : 'truncate max-w-[5rem]'"
  >
    {{ symbol }}
  </span>
</template>
