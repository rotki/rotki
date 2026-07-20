<script setup lang="ts">
const { label = '' } = defineProps<{
  label?: string;
}>();

defineSlots<{
  /** The value shown under the label. */
  default: () => any;
  /** Replaces the plain text label when it needs more than text, e.g. a tooltip. */
  label: () => any;
}>();
</script>

<template>
  <div>
    <RuiDivider />
    <div class="text-right py-4">
      <div class="font-medium pb-2">
        <slot name="label">
          {{ label }}
        </slot>
      </div>
      <slot />
    </div>
  </div>
</template>
