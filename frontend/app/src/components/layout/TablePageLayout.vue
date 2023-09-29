<script setup lang="ts">
withDefaults(defineProps<{ hideHeader?: boolean }>(), {
  hideHeader: false
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div v-if="!hideHeader" class="flex flex-row flex-wrap items-center gap-4">
      <div class="text-body-1 text-rui-text">
        <slot name="title" />
      </div>
      <div class="hidden sm:block sm:grow" />
      <slot name="buttons" />
    </div>
    <div>
      <slot />
    </div>
  </div>
</template>
