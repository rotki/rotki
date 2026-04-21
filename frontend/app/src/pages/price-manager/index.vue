<script setup lang="ts">
import type { TabContent } from '@/modules/core/common/tabs';
import { NoteLocation } from '@/modules/core/common/notes';
import TabNavigation from '@/modules/shell/components/TabNavigation.vue';
import { useAppRoutes } from '@/router/routes';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.PRICE_MANAGER,
  },
  name: 'price-manager',
  props: true,
  redirect: '/price-manager/latest',
});

const { appRoutes } = useAppRoutes();

const tabs = computed<TabContent[]>(() => {
  const Routes = get(appRoutes);
  return [
    Routes.PRICE_MANAGER_LATEST,
    Routes.PRICE_MANAGER_HISTORIC,
    Routes.PRICE_MANAGER_ORACLE,
  ];
});
</script>

<template>
  <TabNavigation
    :tabs="tabs"
    child
  />
</template>
