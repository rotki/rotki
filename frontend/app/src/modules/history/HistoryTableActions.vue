<script lang="ts" setup>
const { hideDivider = false } = defineProps<{ hideDivider?: boolean }>();

defineSlots<{
  default: () => any;
  filter: () => any;
}>();
</script>

<template>
  <div class="flex items-center flex-wrap gap-2 mb-4">
    <slot />
    <div
      v-if="!hideDivider"
      class="grow hidden lg:block"
    />
    <slot name="filter" />
  </div>
</template>
