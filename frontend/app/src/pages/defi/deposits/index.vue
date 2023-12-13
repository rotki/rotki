<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.DEFI_DEPOSITS_PROTOCOLS,
    {
      ...Routes.DEFI_DEPOSITS_LIQUIDITY,
      route: Routes.DEFI_DEPOSITS_LIQUIDITY.route.replace(':location*', '')
    }
  ];
});
</script>

<template>
  <TabNavigation :tabs="tabs" class="decentralized-deposits" />
</template>
