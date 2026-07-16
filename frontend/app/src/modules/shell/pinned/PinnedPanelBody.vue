<script setup lang="ts">
// The single body container every pinned panel renders into (the rail wraps each
// panel in it). Owns the height/scroll contract centrally so a new pinnable area
// cannot get it wrong. Panels provide their own content; the standard content
// gutter is `px-3` (see the pinned panels/content components). Full-width bars
// (tab rows, filters) are expected to span this box edge-to-edge, so the gutter
// lives on the content areas, not here.
defineSlots<{
  default: () => unknown;
}>();
</script>

<template>
  <div class="flex-1 min-h-0 flex flex-col overflow-hidden">
    <slot />
  </div>
</template>
