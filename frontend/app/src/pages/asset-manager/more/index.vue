<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';
import type { ComputedRef } from 'vue';
import type { TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.ASSET_MANAGER_CEX_MAPPING,
    Routes.ASSET_MANAGER_NEWLY_DETECTED,
  ];
});
</script>

<template>
  <TabNavigation
    :tabs="tabs"
    class="asset-manager-more"
  />
</template>
