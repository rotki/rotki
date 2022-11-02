<template>
  <tab-navigation :tab-contents="tabs" class="decentralized-deposits" />
</template>

<script setup lang="ts">
import { ComputedRef } from 'vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { useAppRoutes } from '@/router/routes';
import { TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [Routes.DEFI_DEPOSITS_PROTOCOLS, Routes.DEFI_DEPOSITS_LIQUIDITY];
});
</script>
