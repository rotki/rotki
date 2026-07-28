<script setup lang="ts">
import type { ComponentPublicInstance } from 'vue';
import { onKeyStroke } from '@vueuse/core';

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
// Only the behaviour lives here (scrim, slide-up, placement, modality). Panels bring their own
// header and actions, because the detail surfaces differ too much to share chrome.
const open = defineModel<boolean>({ required: true });

const { height = '95%', label } = defineProps<{
  /** Sheet height, as a CSS length relative to the host panel. */
  height?: string;
  /** Accessible name for the sheet, since the header markup belongs to the panel. */
  label?: string;
}>();

defineSlots<{
  /** Optional sticky title bar, forwarded to the card's header so it does not scroll with the body. */
  header?: () => unknown;
  default: () => unknown;
}>();

const sheetRef = useTemplateRef<ComponentPublicInstance>('sheet');

/** RuiCard is a component, so its ref yields the instance; the trap needs the element. */
const sheet = computed<HTMLElement | undefined>(() => {
  const el = get(sheetRef)?.$el;
  return el instanceof HTMLElement ? el : undefined;
});

/** What had focus before the sheet opened, so closing it does not dump focus on the body. */
let previouslyFocused: HTMLElement | undefined;

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusable(): HTMLElement[] {
  const el = get(sheet);
  if (!el)
    return [];
  // no visibility filter: everything the sheet renders while open is on screen, and the
  // usual `offsetParent` test reports null for every element under jsdom
  return [...el.querySelectorAll<HTMLElement>(FOCUSABLE)];
}

function close(): void {
  set(open, false);
}

onKeyStroke('Escape', (event) => {
  if (!get(open))
    return;
  event.preventDefault();
  close();
});

/**
 * The sheet covers its panel but is not a native dialog, so Tab would otherwise walk straight
 * out into the content behind the scrim. Cycling it by hand keeps the modality honest without
 * pulling in a focus-trap dependency for the one surface that needs it.
 */
onKeyStroke('Tab', (event) => {
  const items = focusable();
  if (!get(open) || items.length === 0)
    return;

  const first = items[0];
  const last = items.at(-1) ?? first;
  const active = document.activeElement;

  if (event.shiftKey && (active === first || !get(sheet)?.contains(active))) {
    event.preventDefault();
    last.focus();
  }
  else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
});

watch(open, async (isOpen) => {
  if (isOpen) {
    previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : undefined;
    await nextTick();
    // the sheet itself takes focus first: its content may start with a scroll area rather
    // than a control, and announcing the surface matters more than reaching a button fast
    (get(sheet) ?? focusable()[0])?.focus();
  }
  else {
    previouslyFocused?.focus();
    previouslyFocused = undefined;
  }
});
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
      ref="sheet"
      no-padding
      role="dialog"
      aria-modal="true"
      :aria-label="label"
      tabindex="-1"
      :style="{ height }"
      class="absolute bottom-0 left-0 right-0 border-t-2 border-rui-primary flex flex-col shadow-lg !rounded-b-none z-10 overflow-hidden focus:outline-none"
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
