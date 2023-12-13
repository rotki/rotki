<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.SETTINGS_GENERAL,
    Routes.SETTINGS_ACCOUNTING,
    Routes.SETTINGS_DATA_SECURITY,
    Routes.SETTINGS_MODULES
  ];
});
</script>

<template>
  <TabNavigation :tabs="tabs" class="settings" />
</template>
