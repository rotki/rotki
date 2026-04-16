<script setup lang="ts">
import type { TabContent } from '@/modules/core/common/tabs';
import SettingsSearch from '@/modules/settings/SettingsSearch.vue';
import TabNavigation from '@/modules/shell/components/TabNavigation.vue';
import { Routes, useAppRoutes } from '@/router/routes';

definePage({
  redirect: Routes.SETTINGS_ACCOUNT,
});

const { t } = useI18n({ useScope: 'global' });

const { appRoutes } = useAppRoutes();

const tabs = computed<TabContent[]>(() => {
  const routes = get(appRoutes);
  return [
    routes.SETTINGS_ACCOUNT,
    routes.SETTINGS_GENERAL,
    routes.SETTINGS_DATABASE,
    routes.SETTINGS_ACCOUNTING,
    routes.SETTINGS_EVM,
    routes.SETTINGS_ORACLE,
    routes.SETTINGS_RPC,
    routes.SETTINGS_MODULES,
    routes.SETTINGS_INTERFACE,
  ];
});
</script>

<template>
  <div class="container lg:px-8">
    <div class="flex flex-wrap items-center justify-between gap-x-8 gap-y-4 mb-6">
      <h5 class="text-h5 font-semibold">
        {{ t('navigation_menu.settings') }}
      </h5>

      <SettingsSearch />
    </div>
    <TabNavigation
      :tabs="tabs"
      plain
      child
      class="settings"
    />
  </div>
</template>
