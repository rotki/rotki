<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.ASSET_MANAGER_MANAGED,
    Routes.ASSET_MANAGER_CUSTOM,
    Routes.ASSET_MANAGER_NEWLY_DETECTED
  ];
});
</script>

<template>
  <TabNavigation :tab-contents="tabs" data-cy="manage-assets-tab" />
</template>
