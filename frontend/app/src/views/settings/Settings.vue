<template>
  <tab-navigation :tab-contents="tabs" class="settings" />
</template>

<script setup lang="ts">
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { routesRef } from '@/router/routes';
import { TabContent } from '@/types/tabs';

const Routes = get(routesRef);

const tabs: TabContent[] = [
  Routes.SETTINGS_GENERAL,
  Routes.SETTINGS_ACCOUNTING,
  Routes.SETTINGS_DATA_SECURITY,
  Routes.SETTINGS_MODULES
];
</script>
