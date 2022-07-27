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
import { computed } from '@vue/composition-api';
import { get } from '@vueuse/core';
import DefiWizard from '@/components/defi/wizard/DefiWizard.vue';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';
import { routesRef } from '@/router/routes';
import { useStore } from '@/store/utils';

const Routes = get(routesRef);

const tabs: TabContent[] = [
  Routes.DEFI_OVERVIEW,
  Routes.DEFI_DEPOSITS,
  Routes.DEFI_LIABILITIES,
  Routes.DEFI_DEX_TRADES,
  Routes.DEFI_AIRDROPS
];

const store = useStore();
const defiSetupDone = computed<boolean>(() => {
  return store.state.settings!.defiSetupDone;
});
</script>

<style scoped lang="scss">
.decentralized-finance {
  height: 100%;
}
</style>
