<script setup lang="ts">
/**
 * The activator for a breadcrumb crumb that opens a menu of sibling pages.
 *
 * @remarks
 * It is drawn as an outlined select, because as plain crumb text first-time users read it as the
 * page title and miss that it opens a menu. Attributes such as `aria-label`, `data-testid` and the
 * menu's activator attrs fall through to the button.
 */
defineSlots<{
  /** The current page: its icon or logo and its name. */
  default: () => any;
}>();
</script>

<template>
  <button
    type="button"
    class="flex items-center gap-2 h-8 pl-2 pr-1.5 rounded-rui-control border border-rui-outline bg-rui-surface text-rui-text hover:bg-rui-hover transition-colors"
  >
    <slot />
    <RuiIcon
      name="lu-chevrons-up-down"
      size="16"
      class="ml-0.5 text-rui-text-secondary"
    />
  </button>
</template>
