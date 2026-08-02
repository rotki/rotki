<script setup lang="ts">
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { usePremium } from '@/modules/premium/use-premium';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import ActiveModules from '@/modules/settings/modules/ActiveModules.vue';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';
import { useSetting } from '@/modules/settings/use-setting';
import LiquityStakingDetails from '@/modules/staking/liquity/LiquityStakingDetails.vue';
import LiquityStakingPagePlaceholder from '@/modules/staking/liquity/LiquityStakingPagePlaceholder.vue';
import { useLiquityDataFetching } from '@/modules/staking/liquity/use-liquity-data-fetching';

const modules = [Module.LIQUITY];
const { enabled: moduleEnabled } = useModuleEnabled(modules[0]);
const { fetchPools, fetchStaking, fetchStatistics } = useLiquityDataFetching();
const { resetProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();
const currencySymbol = useSetting('currencySymbol');
const premium = usePremium();
const { fetchPrices } = usePriceTaskManager();

const LUSD_ID = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0';
const LQTY_ID = 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D';

async function fetch(refresh = false) {
  resetProtocolStatsPriceQueryStatus('liquity');

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
