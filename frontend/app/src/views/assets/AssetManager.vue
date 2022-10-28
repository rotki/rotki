<template>
  <tab-navigation :tab-contents="tabs" data-cy="manage-assets-tab" />
</template>

<script setup lang="ts">
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { routesRef } from '@/router/routes';
import { TabContent } from '@/types/tabs';

const Routes = get(routesRef);

const tabs: TabContent[] = [
  Routes.ASSET_MANAGER_MANAGED,
  Routes.ASSET_MANAGER_CUSTOM
];
</script>
