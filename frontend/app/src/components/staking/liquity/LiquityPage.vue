<script setup lang="ts">
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { useBalancePricesStore } from '@/store/balances/prices';

const modules = [Module.LIQUITY];
const { isModuleEnabled } = useModules();
const { fetchStaking, fetchPools, fetchStatistics } = useLiquityStore();
const { shouldShowLoadingScreen } = useStatusStore();
const moduleEnabled = isModuleEnabled(modules[0]);
const loading = shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING);
const premium = usePremium();
const { fetchPrices } = useBalancePricesStore();

const LUSD_ID = 'eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0';
const LQTY_ID = 'eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D';

const fetch = async (refresh = false) => {
  await Promise.all([
    fetchStaking(refresh),
    fetchPools(refresh),
    fetchStatistics(refresh),
    fetchPrices({
      ignoreCache: refresh,
      selectedAssets: [LUSD_ID, LQTY_ID, 'ETH']
    })
  ]);
};

onMounted(async () => {
  if (get(moduleEnabled)) {
    await fetch();
  }
});

watch(moduleEnabled, async enabled => {
  if (enabled) {
    await fetch();
  }
});

const { tc } = useI18n();
</script>

<template>
  <div>
    <no-premium-placeholder
      v-if="!premium"
      :text="tc('liquity_page.no_premium')"
    />
    <module-not-active v-else-if="!moduleEnabled" :modules="modules" />
    <progress-screen v-else-if="loading">
      <template #message>
        {{ tc('liquity_page.loading') }}
      </template>
    </progress-screen>
    <div v-else>
      <liquity-staking-details @refresh="fetch">
        <template #modules>
          <active-modules :modules="modules" />
        </template>
      </liquity-staking-details>
    </div>
  </div>
</template>
