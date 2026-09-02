<script setup lang="ts">
/**
 * The body container every pinned panel renders into, owning the height and scroll contract so a
 * new pinnable area cannot get it wrong.
 *
 * @remarks
 * No gutter here: full-width bars such as tab rows and filters span this box edge-to-edge, so
 * the `px-3` content gutter lives on the content areas instead.
 */
defineSlots<{
  default: () => unknown;
}>();
</script>

<template>
  <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
    <slot />
  </div>
</template>
