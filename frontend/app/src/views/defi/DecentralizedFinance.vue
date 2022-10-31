<template>
  <div>
    <tab-navigation
      v-if="defiSetupDone"
      :tab-contents="tabs"
      no-content-margin
    />
    <defi-wizard v-else class="mt-8" />
  </div>
</template>

<script setup lang="ts">
import { ComputedRef } from 'vue';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import TabNavigation from '@/components/helper/TabNavigation.vue';
import { useAppRoutes } from '@/router/routes';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { TabContent } from '@/types/tabs';

const { appRoutes } = useAppRoutes();

const tabs: ComputedRef<TabContent[]> = computed(() => {
  const Routes = get(appRoutes);
  return [
    Routes.DEFI_OVERVIEW,
    Routes.DEFI_DEPOSITS,
    Routes.DEFI_LIABILITIES,
    Routes.DEFI_AIRDROPS
  ];
});

const { defiSetupDone } = storeToRefs(useFrontendSettingsStore());
</script>

<style scoped lang="scss">
.decentralized-finance {
  height: 100%;
}
</style>
