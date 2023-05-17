<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { useAppRoutes } from '@/router/routes';
import { type TabContent } from '@/types/tabs';

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

const defi = useDefiStore();
const yearn = useYearnStore();
const aave = useAaveStore();
const compound = useCompoundStore();
const maker = useMakerDaoStore();
const airdrops = useAirdropStore();

const { resetDefiStatus } = useStatusStore();

onUnmounted(() => {
  defi.$reset();
  yearn.$reset();
  aave.$reset();
  compound.$reset();
  maker.$reset();
  airdrops.$reset();
  resetDefiStatus();
});
</script>

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

<style scoped lang="scss">
.decentralized-finance {
  height: 100%;
}
</style>
