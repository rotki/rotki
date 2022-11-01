<template>
  <tab-navigation :tab-contents="tabs" data-cy="manage-assets-tab" />
</template>

<script setup lang="ts">
import { ComputedRef } from 'vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { useAppRoutes } from '@/router/routes';
import { TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [Routes.ASSET_MANAGER_MANAGED, Routes.ASSET_MANAGER_CUSTOM];
});
</script>
