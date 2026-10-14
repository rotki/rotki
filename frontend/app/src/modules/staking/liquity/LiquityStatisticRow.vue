<script setup lang="ts">
const { label = '' } = defineProps<{
  label?: string;
}>();

defineSlots<{
  /** The value shown at the end of the row. */
  default: () => any;
  /** Replaces the plain text label when it needs more than text, e.g. a tooltip. */
  label: () => any;
}>();
</script>

<template>
  <div>
    <RuiDivider />
    <div class="flex items-start justify-between gap-4 py-3">
      <div class="text-rui-text-secondary pt-1">
        <slot name="label">
          {{ label }}
        </slot>
      </div>
      <div class="text-right">
        <slot />
      </div>
    </div>
  </div>
</template>
