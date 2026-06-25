<script setup lang="ts">
/**
 * Layout primitive for dialogs (and the pinned sidebar) that hold a table or
 * other long content which must scroll while the surrounding chrome stays put.
 *
 * It establishes a bounded flex column so the body region absorbs the leftover
 * space and scrolls on its own — no per-dialog `max-h-[calc(100vh - …)]` magic
 * numbers, and no fighting a child component's own `overflow` rules.
 *
 * The `min-h-0` on the body is load-bearing: without it a flex child refuses to
 * shrink below its content and would never scroll. Keeping it here means callers
 * cannot forget it.
 *
 * The root `max-h-[90vh]` matches RuiDialog's own content cap so the dialog's
 * scrollbar never doubles up with ours; `fill` swaps it for `h-full` when the
 * host already provides a fixed height (e.g. the pinned sidebar).
 */
const { fill = false, maxHeight } = defineProps<{
  /**
   * Grow to fill the remaining space of a bounded flex-column parent instead of
   * capping at the dialog's `90vh`. The immediate parent must be `flex flex-col`
   * with a bounded height (e.g. the report card body, the pinned sidebar). Use
   * this for the truly magic-number-free layout.
   */
  fill?: boolean;
  /**
   * Explicit cap for the column, e.g. `calc(100vh - 21.25rem)`. Use when the
   * host can't propagate a flex height down to here (e.g. content nested inside
   * `RuiTabItems`). Ignored when `fill` is set.
   */
  maxHeight?: string;
}>();

defineSlots<{
  /** Pinned above the scroll area (title bar, stepper, …). */
  header?: () => any;
  /** The scrollable region (usually a table). */
  default: () => any;
  /** Pinned below the scroll area (action buttons, hints, …). */
  footer?: () => any;
}>();

const boundClass = computed<string>(() => {
  if (fill)
    return 'flex-1';

  return maxHeight ? '' : 'max-h-[90vh]';
});

const boundStyle = computed<Record<string, string> | undefined>(() =>
  (!fill && maxHeight) ? { maxHeight } : undefined,
);
</script>

<template>
  <div
    class="flex flex-col min-h-0"
    :class="[boundClass]"
    :style="boundStyle"
  >
    <div
      v-if="$slots.header"
      class="shrink-0"
    >
      <slot name="header" />
    </div>
    <div class="flex-1 min-h-0 overflow-y-auto scroll-smooth">
      <slot />
    </div>
    <div
      v-if="$slots.footer"
      class="shrink-0"
    >
      <slot name="footer" />
    </div>
  </div>
</template>
