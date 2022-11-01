<template>
  <tab-navigation :tab-contents="tabs" data-cy="manage-prices-tab" />
</template>

<script setup lang="ts">
import { ComputedRef } from 'vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { useAppRoutes } from '@/router/routes';
import { TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [Routes.PRICE_MANAGER_LATEST, Routes.PRICE_MANAGER_HISTORIC];
});
</script>
