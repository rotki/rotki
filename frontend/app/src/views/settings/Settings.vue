<template>
  <tab-navigation :tab-contents="tabs" class="settings" />
</template>

<script setup lang="ts">
import { ComputedRef } from 'vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { useAppRoutes } from '@/router/routes';
import { TabContent } from '@/types/tabs';

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
