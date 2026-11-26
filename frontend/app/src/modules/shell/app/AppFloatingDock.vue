<script setup lang="ts">
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { watchImmediate } from '@vueuse/core';
import { useCoreScroll } from '@/modules/shell/layout/use-core-scroll';
import TaskDock from '@/modules/task-center/components/TaskDock.vue';

/** The height of the dock's pill; the expanded panel overlays the page and reserves no room. */
const dockHeight = defineModel<number>('dockHeight', { default: 0 });

const { scrollToTop, shouldShowScrollToTopButton } = useCoreScroll();

/**
 * The same room for panels docked on the right, such as the pinned rail, whose bottom the dock
 * covers: its height, its 1rem offset and a gap, plus however far it rises above a stuck table bar.
 */
watchImmediate(dockHeight, (height) => {
  const style = document.documentElement.style;
  if (height > 0)
    style.setProperty('--rotki-dock-inset', `calc(${height}px + 1.5rem + var(--rui-sticky-bottom, 0px))`);
  else
    style.removeProperty('--rotki-dock-inset');
});
</script>

<template>
  <div class="fixed right-4 bottom-[calc(1rem+var(--rui-sticky-bottom))] z-rui-floating flex flex-col items-end gap-3 max-w-[calc(100vw-2rem)] transition-[bottom]">
    <Transition
      enter-from-class="opacity-0"
      enter-to-class="opacity-1"
      enter-active-class="transition duration-300"
      leave-from-class="opacity-1"
      leave-to-class="opacity-0"
      leave-active-class="transition duration-100"
    >
      <RuiButton
        v-if="shouldShowScrollToTopButton"
        color="primary"
        variant="fab"
        size="lg"
        icon
        class="max-sm:fixed max-sm:left-4 max-sm:bottom-[calc(1rem+var(--rui-sticky-bottom))]"
        @click="scrollToTop()"
      >
        <RuiIcon name="lu-arrow-up" />
      </RuiButton>
    </Transition>
    <div class="flex flex-col items-end max-w-full empty:hidden">
      <TaskDock v-model:bar-height="dockHeight" />
    </div>
  </div>
</template>
