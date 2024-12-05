<script setup lang="ts">
import { useAreaVisibilityStore } from '@/store/session/visibility';

const ReportActionableCard = defineAsyncComponent(() => import('@/components/profitloss/ReportActionableCard.vue'));

const { pinned, showPinned } = storeToRefs(useAreaVisibilityStore());

const { isLgAndDown } = useBreakpoint();

const component: ComputedRef = computed(() => {
  const pinnedValue = get(pinned);
  if (pinnedValue && pinnedValue.name === 'report-actionable-card')
    return ReportActionableCard;

  return null;
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="showPinned"
    :temporary="isLgAndDown"
    width="500px"
    position="right"
    class="border-l border-rui-grey-300 dark:border-rui-grey-800 z-[6]"
  >
    <div>
      <Component
        :is="component"
        v-if="pinned && component"
        v-bind="pinned.props"
      />
    </div>
  </RuiNavigationDrawer>
</template>
