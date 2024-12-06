<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import type { TabContent } from '@/types/tabs';

definePage({
  name: 'defi-deposits',
  redirect: '/defi/deposits/protocols',
});

const { appRoutes } = useAppRoutes();

const tabs = computed<TabContent[]>(() => {
  const Routes = get(appRoutes);
  return [
    Routes.DEFI_DEPOSITS_PROTOCOLS,
    {
      ...Routes.DEFI_DEPOSITS_LIQUIDITY,
      route: '/defi/deposits/liquidity',
    },
  ];
});
</script>

<template>
  <TabNavigation
    :tabs="tabs"
    class="decentralized-deposits"
  />
</template>
