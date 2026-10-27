<script setup lang="ts">
/** One labelled value in an issue's summary; the warning tone marks the value that is wrong. */
const { label, warning = false } = defineProps<{
  label: string;
  warning?: boolean;
}>();

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <div
    class="flex min-w-0 flex-col gap-0.5 overflow-hidden rounded-md px-3 py-2"
    :class="warning ? 'bg-rui-warning/10' : 'bg-rui-grey-50 dark:bg-rui-grey-900'"
  >
    <span
      class="text-xs"
      :class="warning ? 'text-rui-warning' : 'text-rui-text-secondary'"
    >
      {{ label }}
    </span>
    <slot />
  </div>
</template>
