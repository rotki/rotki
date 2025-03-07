<script setup lang="ts">
import type { TabContent } from '@/types/tabs';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { Routes, useAppRoutes } from '@/router/routes';

definePage({
  redirect: Routes.SETTINGS_ACCOUNT,
});

const { t } = useI18n();

const { appRoutes } = useAppRoutes();

const tabs = computed<TabContent[]>(() => {
  const Routes = get(appRoutes);
  return [
    Routes.SETTINGS_ACCOUNT,
    Routes.SETTINGS_GENERAL,
    Routes.SETTINGS_DATABASE,
    Routes.SETTINGS_ACCOUNTING,
    Routes.SETTINGS_ORACLE,
    Routes.SETTINGS_RPC,
    Routes.SETTINGS_MODULES,
    Routes.SETTINGS_INTERFACE,
  ];
});
</script>

<template>
  <div class="container lg:px-8">
    <h5 class="text-h5 font-semibold mb-6">
      {{ t('navigation_menu.settings') }}
    </h5>
    <TabNavigation
      :tabs="tabs"
      plain
      child
      class="settings"
    />
  </div>
</template>
