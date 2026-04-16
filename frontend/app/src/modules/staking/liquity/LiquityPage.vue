<script setup lang="ts">
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { Section } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';
import { usePremium } from '@/modules/premium/use-premium';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import ActiveModules from '@/modules/settings/modules/ActiveModules.vue';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import LiquityStakingDetails from '@/modules/staking/liquity/LiquityStakingDetails.vue';
import LiquityStakingPagePlaceholder from '@/modules/staking/liquity/LiquityStakingPagePlaceholder.vue';
import { useLiquityDataFetching } from '@/modules/staking/liquity/use-liquity-data-fetching';
import { useLiquityStore } from '@/modules/staking/liquity/use-liquity-store';

const modules = [Module.LIQUITY];
const { enabled: moduleEnabled } = useModuleEnabled(modules[0]);
const { setStakingQueryStatus } = useLiquityStore();
const { fetchPools, fetchStaking, fetchStatistics } = useLiquityDataFetching();
const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();
const { useShouldShowLoadingScreen } = useStatusStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const premium = usePremium();
const { fetchPrices } = usePriceTaskManager();

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

watchImmediate(moduleEnabled, async (enabled) => {
  if (enabled)
    await fetch();
});

watch(currencySymbol, async () => {
  if (get(moduleEnabled)) {
    await fetch(true);
  }
});

watch(useShouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING), async (current, old) => {
  if (!old && current)
    await fetchStaking();
});

watch(useShouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING_POOLS), async (current, old) => {
  if (!old && current)
    await fetchPools();
});

watch(useShouldShowLoadingScreen(Section.DEFI_LIQUITY_STATISTICS), async (current, old) => {
  if (!old && current)
    await fetchStatistics();
});

const { t } = useI18n({ useScope: 'global' });
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
