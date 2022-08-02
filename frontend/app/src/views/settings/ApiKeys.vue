<template>
  <tab-navigation class="api-keys" :tab-contents="tabs" />
</template>

<script setup lang="ts">
import { get } from '@vueuse/core';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { routesRef } from '@/router/routes';

const Routes = get(routesRef);

const tabs: TabContent[] = [
  Routes.API_KEYS_ROTKI_PREMIUM,
  Routes.API_KEYS_EXCHANGES,
  Routes.API_KEYS_EXTERNAL_SERVICES
];
</script>
