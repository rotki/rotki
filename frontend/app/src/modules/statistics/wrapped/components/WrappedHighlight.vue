<script setup lang="ts">
/**
 * One headline figure: a quiet label over the value, and a line of detail under it. The detail line
 * is kept when empty, so every tile in the row is as tall as the one that has it.
 */
defineProps<{
  label: string;
}>();

defineSlots<{
  default: () => any;
  detail?: () => any;
}>();
</script>

<template>
  <div
    class="flex flex-col gap-1 p-4 md:rounded-rui-card md:border md:border-rui-divider md:bg-rui-surface max-md:[&+&]:border-t max-md:border-rui-divider"
    data-testid="wrapped-highlight"
  >
    <div class="text-sm text-rui-text-secondary">
      {{ label }}
    </div>
    <div class="truncate text-xl font-semibold text-rui-text tabular-nums">
      <slot />
    </div>
    <div class="flex items-baseline gap-1 min-h-5 text-sm text-rui-text-secondary tabular-nums max-md:empty:hidden">
      <slot name="detail" />
    </div>
  </div>
</template>
