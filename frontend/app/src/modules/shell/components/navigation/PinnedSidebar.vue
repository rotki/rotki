<script setup lang="ts">
import type { Component } from 'vue';
import type { Pinned } from '@/modules/session/types';
import { PINNED_CAP, useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useSidebarResize } from '@/modules/shell/layout/use-sidebar-resize';
import { PINNED_PANELS } from '@/modules/shell/pinned/pinned-registry';
import PinnedPanelBody from '@/modules/shell/pinned/PinnedPanelBody.vue';
import { usePinnedTabs } from '@/modules/shell/pinned/use-pinned-tabs';

defineOptions({
  // Two root nodes (mini-bar + drawer); the rail's visibility is driven by the
  // store, so parent attribute fallthrough is intentionally dropped.
  inheritAttrs: false,
});

const store = useAreaVisibilityStore();
const { pinnedPanels, showPinned } = storeToRefs(store);
const { activePinnedId, close, focus, tabs } = usePinnedTabs();

const { t } = useI18n({ useScope: 'global' });
const { isLgAndDown } = useBreakpoint();

const activePanel = computed<Pinned | undefined>(() =>
  get(pinnedPanels).find(panel => panel.name === get(activePinnedId)));

const activeComponent = computed<Component | undefined>(() => {
  const panel = get(activePanel);
  return panel ? PINNED_PANELS[panel.name].component : undefined;
});

/** Panel-specific controls for the active tab, rendered on the tab strip (e.g. ITC settings). */
const activeActions = computed<Component | undefined>(() => {
  const id = get(activePinnedId);
  return id ? PINNED_PANELS[id].actions : undefined;
});

/** Collapsed icon rail: shown on desktop when panels are pinned but the rail is hidden. */
const showMiniBar = computed<boolean>(() =>
  get(tabs).length > 0 && !get(showPinned) && !get(isLgAndDown));

const { dragging, widthPx, onPointerDown, onPointerMove, onPointerUp } = useSidebarResize();

function collapse(): void {
  set(showPinned, false);
}
</script>

<template>
  <!-- Collapsed state: a thin vertical strip of tool icons on the right edge. -->
  <div
    v-if="showMiniBar"
    class="fixed right-0 top-1/2 -translate-y-1/2 z-[6] flex flex-col gap-1 p-1.5 bg-white dark:bg-rui-grey-900 border border-r-0 border-rui-grey-300 dark:border-rui-grey-800 rounded-l-lg shadow-md"
    data-testid="pinned-mini-bar"
  >
    <RuiTooltip
      v-for="tab in tabs"
      :key="tab.name"
      :popper="{ placement: 'left' }"
      :open-delay="300"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :class="tab.name === activePinnedId ? '!bg-rui-primary !text-white' : '!text-rui-text-secondary'"
          :data-testid="`pinned-mini-${tab.name}`"
          @click="focus(tab.name)"
        >
          <RuiIcon
            :name="tab.icon"
            size="18"
          />
        </RuiButton>
      </template>
      {{ t(tab.labelKey) }}
    </RuiTooltip>
  </div>

  <RuiNavigationDrawer
    v-model="showPinned"
    :temporary="isLgAndDown"
    :width="widthPx"
    position="right"
    class="border-l border-rui-grey-300 dark:border-rui-grey-800 z-[6]"
    :class="{ '!transition-none': dragging }"
  >
    <div class="relative h-full">
      <div
        v-if="!isLgAndDown"
        class="absolute left-0 top-0 h-full w-3 -ml-1.5 cursor-col-resize z-20 group flex items-center justify-center"
        @pointerdown="onPointerDown($event)"
        @pointermove="onPointerMove($event)"
        @pointerup="onPointerUp($event)"
        @pointercancel="onPointerUp($event)"
      >
        <div
          class="absolute left-1/2 -translate-x-1/2 top-0 h-full w-[2px] transition-colors pointer-events-none"
          :class="dragging ? 'bg-rui-primary' : 'group-hover:bg-rui-primary/30'"
        />
        <div
          class="rounded-full pointer-events-none z-[1] transition-colors py-1 w-3.5 flex items-center justify-center"
          :class="dragging ? 'bg-rui-primary text-white' : 'bg-rui-grey-300 dark:bg-rui-grey-800 text-rui-grey-600 dark:text-rui-grey-400 group-hover:bg-rui-grey-400 group-hover:dark:bg-rui-grey-700'"
        >
          <RuiIcon
            name="lu-equal"
            size="20"
            class="rotate-90"
          />
        </div>
      </div>

      <div class="h-full flex flex-col">
        <!-- Tab strip: the single title + close + collapse bar for the rail (always shown while pinned).
             Tabs scroll horizontally; the actions + collapse cluster stays pinned to the right. -->
        <div
          v-if="tabs.length > 0"
          class="flex items-stretch shrink-0 bg-rui-grey-100 dark:bg-rui-grey-900 border-b border-default"
        >
          <div class="flex items-stretch overflow-x-auto min-w-0 flex-1">
            <button
              v-for="tab in tabs"
              :key="tab.name"
              type="button"
              class="flex items-center gap-1.5 px-3 py-2 text-caption border-r border-default whitespace-nowrap transition-colors"
              :class="tab.name === activePinnedId
                ? 'bg-rui-primary text-white'
                : 'text-rui-text-secondary hover:bg-rui-grey-200 dark:hover:bg-rui-grey-800'"
              :data-testid="`pinned-tab-${tab.name}`"
              @click="focus(tab.name)"
            >
              <RuiIcon
                :name="tab.icon"
                size="16"
              />
              <span class="max-w-[10rem] truncate">{{ t(tab.labelKey) }}</span>
              <RuiIcon
                name="lu-x"
                size="14"
                class="ml-1 opacity-60 hover:opacity-100"
                :data-testid="`pinned-tab-close-${tab.name}`"
                @click.stop="close(tab.name)"
              />
            </button>
          </div>

          <div class="flex items-center shrink-0 border-l border-default px-1 gap-0.5">
            <Component
              :is="activeActions"
              v-if="activeActions"
            />
            <button
              type="button"
              class="flex items-center p-1 rounded text-rui-text-secondary hover:bg-rui-grey-200 dark:hover:bg-rui-grey-800"
              data-testid="pinned-collapse"
              @click="collapse()"
            >
              <RuiIcon
                name="lu-chevron-right"
                size="18"
              />
            </button>
          </div>
        </div>

        <!-- Active panel, kept alive so backgrounded panels retain their state.
             PinnedPanelBody enforces the shared height/scroll contract for every panel. -->
        <PinnedPanelBody>
          <KeepAlive :max="PINNED_CAP">
            <Component
              :is="activeComponent"
              v-if="activePanel && activeComponent"
              :key="activePinnedId"
              v-bind="activePanel.props"
            />
          </KeepAlive>
        </PinnedPanelBody>
      </div>
    </div>
  </RuiNavigationDrawer>
</template>
