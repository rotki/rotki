<script setup lang="ts">
withDefaults(defineProps<{ hideHeader?: boolean }>(), {
  hideHeader: false
});
</script>

<template>
  <div>
    <div v-if="!hideHeader" class="flex flex-row flex-wrap items-center gap-2">
      <slot name="title" />
      <div class="hidden sm:block sm:grow" />
      <slot name="buttons" />
    </div>
    <div class="mt-8">
      <slot />
    </div>
  </div>
</template>
