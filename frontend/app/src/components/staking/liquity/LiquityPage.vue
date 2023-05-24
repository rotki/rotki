<script setup lang="ts">
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const modules = [Module.LIQUITY];
const { isModuleEnabled } = useModules();
const { fetchStaking, fetchPools, fetchStatistics } = useLiquityStore();
const { shouldShowLoadingScreen } = useStatusStore();
const moduleEnabled = isModuleEnabled(modules[0]);
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

watch(
  shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING),
  async (current, old) => {
    if (!old && current) {
      await fetchStaking();
    }
  }
);

watch(
  shouldShowLoadingScreen(Section.DEFI_LIQUITY_STAKING_POOLS),
  async (current, old) => {
    if (!old && current) {
      await fetchPools();
    }
  }
);

watch(
  shouldShowLoadingScreen(Section.DEFI_LIQUITY_STATISTICS),
  async (current, old) => {
    if (!old && current) {
      await fetchStatistics();
    }
  }
);

const { t } = useI18n();
</script>

<template>
  <div>
    <no-premium-placeholder
      v-if="!premium"
      :text="t('liquity_page.no_premium')"
    />
    <module-not-active v-else-if="!moduleEnabled" :modules="modules" />
    <liquity-staking-details v-else @refresh="fetch($event)">
      <template #modules>
        <active-modules :modules="modules" />
      </template>
    </liquity-staking-details>
  </div>
</template>
