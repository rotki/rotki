<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';
import type { TabContent } from '@/types/tabs';

definePage({
  redirect: '/settings/general',
});

const { appRoutes } = useAppRoutes();

const tabs = computed<TabContent[]>(() => {
  const Routes = get(appRoutes);
  return [Routes.SETTINGS_GENERAL, Routes.SETTINGS_ACCOUNTING, Routes.SETTINGS_DATA_SECURITY, Routes.SETTINGS_MODULES];
});
</script>

<template>
  <TabNavigation
    :tabs="tabs"
    class="settings"
  />
</template>
