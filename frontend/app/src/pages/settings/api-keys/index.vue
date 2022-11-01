<template>
  <tab-navigation class="api-keys" :tab-contents="tabs" />
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
    Routes.API_KEYS_ROTKI_PREMIUM,
    Routes.API_KEYS_EXCHANGES,
    Routes.API_KEYS_EXTERNAL_SERVICES
  ];
});
</script>
