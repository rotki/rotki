<script lang="ts" setup>
withDefaults(defineProps<{ hideDivider?: boolean }>(), { hideDivider: false });
</script>

<template>
  <div class="flex flex-row items-center flex-wrap gap-2 mb-4">
    <slot />
    <div v-if="!hideDivider" class="grow xs:hidden md:block" />
    <div class="flex-1 md:min-w-[20rem]">
      <slot name="filter" />
    </div>
  </div>
</template>
