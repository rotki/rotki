<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [Routes.DEFI_DEPOSITS_PROTOCOLS, Routes.DEFI_DEPOSITS_LIQUIDITY];
});
</script>

<template>
  <TabNavigation :tab-contents="tabs" class="decentralized-deposits" />
</template>
