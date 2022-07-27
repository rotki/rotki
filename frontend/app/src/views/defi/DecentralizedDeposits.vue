<template>
  <tab-navigation :tab-contents="tabs" class="decentralized-deposits" />
</template>

<script setup lang="ts">
import { get } from '@vueuse/core';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { routesRef } from '@/router/routes';

const Routes = get(routesRef);
const tabs: TabContent[] = [
  Routes.DEFI_DEPOSITS_PROTOCOLS,
  Routes.DEFI_DEPOSITS_LIQUIDITY
];
</script>
