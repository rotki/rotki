<script setup lang="ts">
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import LiquityStakingDetails from '@/components/staking/liquity/LiquityStakingDetails.vue';
import LiquityStakingPagePlaceholder from '@/components/staking/liquity/LiquityStakingPagePlaceholder.vue';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useLiquityStore } from '@/store/defi/liquity';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useStatusStore } from '@/store/status';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const modules = [Module.LIQUITY];
const { isModuleEnabled } = useModules();
const { fetchPools, fetchStaking, fetchStatistics, setStakingQueryStatus } = useLiquityStore();
const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();
const { shouldShowLoadingScreen } = useStatusStore();
const moduleEnabled = isModuleEnabled(modules[0]);
const premium = usePremium();
const { fetchPrices } = useBalancePricesStore();

const LUSD_ID = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0';
const LQTY_ID = 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D';

async function fetch(refresh = false) {
  resetProtocolStatsPriceQueryStatus('liquity');
  setStakingQueryStatus(null);

  await Promise.all([
    fetchStaking(refresh),
    fetchPools(refresh),
    fetchStatistics(refresh),
    fetchPrices({
      ignoreCache: refresh,
      selectedAssets: [LUSD_ID, LQTY_ID, 'ETH'],
    }),
  ]);
}

onMounted(async () => {
  if (get(moduleEnabled))
    await fetch();
});

watch(moduleEnabled, async (enabled) => {
  if (enabled)
    await fetch();
});

watch(shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING), async (current, old) => {
  if (!old && current)
    await fetchStaking();
});

watch(shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING_POOLS), async (current, old) => {
  if (!old && current)
    await fetchPools();
});

watch(shouldShowLoadingScreen(Section.DEFI_LIQUITY_STATISTICS), async (current, old) => {
  if (!old && current)
    await fetchStatistics();
});

const { t } = useI18n();
</script>

<template>
  <div>
    <LiquityStakingPagePlaceholder
      v-if="!premium"
      :text="t('liquity_page.no_premium')"
    />
    <ModuleNotActive
      v-else-if="!moduleEnabled"
      :modules="modules"
    />
    <LiquityStakingDetails
      v-else
      @refresh="fetch($event)"
    >
      <template #modules>
        <ActiveModules :modules="modules" />
      </template>
    </LiquityStakingDetails>
  </div>
</template>
