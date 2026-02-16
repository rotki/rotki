<script setup lang="ts">
import { useSidebarResize } from '@/composables/use-sidebar-resize';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const ReportActionableCard = defineAsyncComponent(() => import('@/components/profitloss/ReportActionableCard.vue'));
const MatchAssetMovementsPinned = defineAsyncComponent(() => import('@/components/history/events/MatchAssetMovementsPinned.vue'));

const { pinned, showPinned } = storeToRefs(useAreaVisibilityStore());

const { isLgAndDown } = useBreakpoint();

const component = computed<typeof ReportActionableCard | typeof MatchAssetMovementsPinned | undefined>(() => {
  const pinnedValue = get(pinned);
  if (pinnedValue && pinnedValue.name === 'report-actionable-card')
    return ReportActionableCard;

  if (pinnedValue && pinnedValue.name === 'match-asset-movements-pinned')
    return MatchAssetMovementsPinned;

  return undefined;
});

const { dragging, widthPx, onPointerDown, onPointerMove, onPointerUp } = useSidebarResize();
</script>

<template>
  <RuiNavigationDrawer
    v-model="showPinned"
    :temporary="isLgAndDown"
    :width="widthPx"
    position="right"
    class="border-l border-rui-grey-300 dark:border-rui-grey-800 z-[6] transition"
  >
    <div class="relative h-full">
      <div
        v-if="!isLgAndDown"
        class="absolute left-0 top-0 h-full w-3 -ml-1.5 cursor-col-resize z-20 group flex items-center justify-center"
        @pointerdown="onPointerDown($event)"
        @pointermove="onPointerMove($event)"
        @pointerup="onPointerUp($event)"
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
      <Component
        :is="component"
        v-if="pinned && component"
        v-bind="pinned.props"
      />
    </div>
  </RuiNavigationDrawer>
</template>
