<script setup lang="ts">
defineSlots<{
  toolbar?: () => any;
  default: () => any;
}>();
</script>

<template>
  <!--
    One surface for a table and the controls that act on it, so they read as a unit instead of a
    toolbar floating on the page above a separate box. Not a RuiCard: the card's scrolling content
    would be the scroll box the table's sticky pagination bar binds to. `overflow-clip` rounds the
    table's corners without creating one. The table inside goes without its own outline.
  -->
  <!-- the frame rounds and outlines, so the table directly inside is square and borderless; nested tables keep theirs -->
  <section class="rounded-rui-card border border-rui-divider bg-rui-surface overflow-clip [&>[data-id=table-wrapper]]:rounded-none [&>[data-id=table-wrapper]]:border-0">
    <div
      v-if="$slots.toolbar"
      class="flex flex-wrap items-center gap-3 p-3 border-b border-rui-divider"
      data-testid="table-toolbar"
    >
      <slot name="toolbar" />
    </div>
    <slot />
  </section>
</template>
