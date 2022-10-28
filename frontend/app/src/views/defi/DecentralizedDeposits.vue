<template>
  <tab-navigation :tab-contents="tabs" class="decentralized-deposits" />
</template>

<script setup lang="ts">
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { routesRef } from '@/router/routes';
import { TabContent } from '@/types/tabs';

const Routes = get(routesRef);
const tabs: TabContent[] = [
  Routes.DEFI_DEPOSITS_PROTOCOLS,
  Routes.DEFI_DEPOSITS_LIQUIDITY
];
</script>
