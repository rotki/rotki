<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

// Bottom sheet for a detail surface opened from inside a pinned panel: it slides up over the
// panel's own body rather than opening yet another drawer beside the rail.
//
// It is positioned `absolute` on purpose, so the host panel must be `relative`. A teleporting
// overlay (RuiNavigationDrawer/RuiDialog) is NOT usable here: the rail keeps backgrounded panels
// alive with <KeepAlive>, and a deactivated panel's teleported content leaks out of / empties its
// target. Absolute positioning keeps the sheet inside the panel it belongs to.
//
// Only the behaviour lives here (scrim, slide-up, placement). Panels bring their own header and
// actions, because the detail surfaces differ too much to share chrome.
const open = defineModel<boolean>({ required: true });

const { height = '95%' } = defineProps<{
  /** Sheet height, as a CSS length relative to the host panel. */
  height?: string;
}>();

defineSlots<{
  /** Optional sticky title bar, forwarded to the card's header so it does not scroll with the body. */
  header?: () => unknown;
  default: () => unknown;
}>();

function close(): void {
  set(open, false);
}
</script>

<template>
  <Transition
    enter-active-class="transition-opacity duration-300"
    leave-active-class="transition-opacity duration-300"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <div
      v-if="open"
      class="absolute inset-0 bg-black/50"
      data-testid="pinned-detail-sheet-scrim"
      @click="close()"
    />
  </Transition>

  <Transition
    enter-active-class="transition-transform duration-300 ease-out"
    leave-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-y-full"
    leave-to-class="translate-y-full"
  >
    <RuiCard
      v-if="open"
      no-padding
      :style="{ height }"
      class="absolute bottom-0 left-0 right-0 border-t-2 border-rui-primary flex flex-col shadow-lg !rounded-b-none z-10 overflow-hidden"
      content-class="h-full"
      data-testid="pinned-detail-sheet"
      v-bind="$attrs"
    >
      <template
        v-if="$slots.header"
        #custom-header
      >
        <slot name="header" />
      </template>
      <slot />
    </RuiCard>
  </Transition>
</template>
