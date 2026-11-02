<script setup lang="ts">
/**
 * The frame of the address interactions card, shared by the graph and its premium placeholder so the
 * placeholder follows any change to the layout.
 *
 * @remarks
 * On wide screens the card fills the window below the page header, so the graph never scrolls off
 * and only the side panel scrolls. Its height subtracts 9.25rem: the app bar, the page's top and
 * bottom padding, and the header row with its gap. The page sets `scrollsItself`, so the shell adds
 * no room for the task dock; the side panel clears the dock through `--rotki-dock-inset` instead.
 */
defineSlots<{
  /** The filters across the top of the card. */
  header: () => unknown;
  /** A notice between the filters and the graph. */
  banner?: () => unknown;
  /** The graph area, which takes the remaining height. */
  default: () => unknown;
  /** The hints below the graph. */
  footer: () => unknown;
  /** The side panel, the only part that scrolls. */
  panel: () => unknown;
}>();
</script>

<template>
  <section class="relative flex flex-col overflow-hidden rounded-xl border border-default bg-rui-surface text-rui-text xl:h-[calc(100dvh-9.25rem)] xl:min-h-[36rem]">
    <slot name="header" />
    <div class="grid min-h-0 flex-1 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="flex min-h-0 min-w-0 flex-col">
        <slot name="banner" />
        <div class="relative flex min-h-0 flex-1 flex-col">
          <slot />
        </div>
        <div class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-default px-4 py-2">
          <slot name="footer" />
        </div>
      </div>
      <aside class="min-h-0 min-w-0 border-t border-default pb-(--rotki-dock-inset) xl:overflow-y-auto xl:overscroll-contain xl:border-t-0 xl:border-l">
        <slot name="panel" />
      </aside>
    </div>
  </section>
</template>
