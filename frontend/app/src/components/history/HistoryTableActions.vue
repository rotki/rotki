<script lang="ts" setup>
withDefaults(defineProps<{ hideDivider?: boolean }>(), { hideDivider: false });
</script>

<template>
  <div class="flex flex-row items-center flex-wrap gap-2 mb-4">
    <slot />
    <div v-if="!hideDivider" class="grow hidden lg:block" />
    <slot name="filter" />
  </div>
</template>
