<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type TabContent } from '@/types/tabs';

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

<template>
  <TabNavigation :tab-contents="tabs" data-cy="accounts-balances-tab" />
</template>
