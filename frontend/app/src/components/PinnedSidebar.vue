<script setup lang="ts">
import { type ComputedRef } from 'vue';

const props = defineProps<{ visible: boolean }>();

const emit = defineEmits<{
  (e: 'update:visible', visible: boolean): void;
}>();

const display = useVModel(props, 'visible', emit);

const ReportActionableCard = defineAsyncComponent(
  () => import('@/components/profitloss/ReportActionableCard.vue')
);

const { pinned } = storeToRefs(useAreaVisibilityStore());

const component: ComputedRef = computed(() => {
  const pinnedValue = get(pinned);
  if (pinnedValue && pinnedValue.name === 'report-actionable-card') {
    return ReportActionableCard;
  }
  return null;
});
</script>

<template>
  <VNavigationDrawer
    v-model="display"
    class="pinned-sidebar"
    clipped
    width="560px"
    right
    temporary
    hide-overlay
  >
    <div>
      <Component
        :is="component"
        v-if="pinned && component"
        v-bind="pinned.props"
      />
    </div>
  </VNavigationDrawer>
</template>

<style scoped lang="scss">
.pinned-sidebar {
  top: 64px !important;
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);
  padding-top: 0 !important;
  border-top: var(--v-rotki-light-grey-darken1) solid thin;

  &--mobile {
    top: 56px !important;
  }

  &.v-navigation-drawer {
    &--is-mobile {
      padding-top: 0 !important;
    }
  }
}
</style>
