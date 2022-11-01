<template>
  <tab-navigation :tab-contents="tabs" data-cy="accounts-balances-tab" />
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
    Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
    Routes.ACCOUNTS_BALANCES_EXCHANGE,
    Routes.ACCOUNTS_BALANCES_MANUAL,
    Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE
  ];
});
</script>
