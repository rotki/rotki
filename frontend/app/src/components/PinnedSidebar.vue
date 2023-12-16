<script setup lang="ts">
const display = defineModel<boolean>({ required: true });

const ReportActionableCard = defineAsyncComponent(() => import('@/components/profitloss/ReportActionableCard.vue'));

const { pinned } = storeToRefs(useAreaVisibilityStore());

const component: ComputedRef = computed(() => {
  const pinnedValue = get(pinned);
  if (pinnedValue && pinnedValue.name === 'report-actionable-card')
    return ReportActionableCard;

  return null;
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="display"
    width="560px"
    temporary
    position="right"
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
