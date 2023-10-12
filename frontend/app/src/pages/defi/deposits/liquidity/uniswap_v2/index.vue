<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { LpType } from '@rotki/common/lib/defi';
import { type XswapBalance } from '@rotki/common/lib/defi/xswap';
import { type ComputedRef } from 'vue';
import { UniswapDetails } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const modules = [Module.UNISWAP];
const chains = [Blockchain.ETH];

const selectedAccounts = ref<GeneralAccount[]>([]);
const selectedPools = ref<string[]>([]);

const store = useUniswapStore();

const {
  fetchEvents,
  fetchV2Balances: fetchBalances,
  uniswapV2Balances: uniswapBalances,
  uniswapPoolProfit
} = store;

const { uniswapV2Addresses: addresses, uniswapV2PoolAssets: poolAssets } =
  storeToRefs(store);

const { isModuleEnabled } = useModules();
const { isLoading, shouldShowLoadingScreen } = useStatusStore();

const { t } = useI18n();
const { premiumURL } = useInterop();

const enabled = isModuleEnabled(modules[0]);
const loading = shouldShowLoadingScreen(Section.DEFI_UNISWAP_V2_BALANCES);
const primaryRefreshing = isLoading(Section.DEFI_UNISWAP_V2_BALANCES);
const secondaryRefreshing = isLoading(Section.DEFI_UNISWAP_EVENTS);
const premium = usePremium();

const selectedAddresses = useArrayMap(selectedAccounts, a => a.address);

const balances: ComputedRef<XswapBalance[]> = computed(() => {
  const addresses = get(selectedAddresses);
  const pools = get(selectedPools);
  const balances = get(uniswapBalances(addresses));
  return pools.length === 0
    ? balances
    : balances.filter(({ address }) => pools.includes(address));
});

const poolProfit = computed(() => {
  const addresses = get(selectedAddresses);
  const pools = get(selectedPools);
  const profit = get(uniswapPoolProfit(addresses));
  return pools.length === 0
    ? profit
    : profit.filter(({ poolAddress }) => pools.includes(poolAddress));
});

const refresh = async () => {
  await Promise.all([fetchBalances(true), fetchEvents(true)]);
};

const getIdentifier = (item: XswapBalance) => item.address;

onMounted(async () => {
  await Promise.all([fetchBalances(false), fetchEvents(false)]);
});

const lpType = LpType.UNISWAP_V2;
</script>

<template>
  <ModuleNotActive v-if="!enabled" :modules="modules" />
  <ProgressScreen v-else-if="loading">
    <template #message>
      {{ t('uniswap.loading') }}
    </template>
    <template v-if="!premium" #default>
      <i18n tag="div" path="uniswap.loading_non_premium">
        <BaseExternalLink :text="t('uniswap.premium')" :href="premiumURL" />
      </i18n>
    </template>
  </ProgressScreen>
  <div v-else class="uniswap flex flex-col gap-4">
    <RefreshHeader
      :title="t('uniswap.title', { v: 2 })"
      class="mt-4"
      :loading="primaryRefreshing || secondaryRefreshing"
      @refresh="refresh()"
    >
      <template #actions>
        <ActiveModules :modules="modules" />
      </template>
    </RefreshHeader>
    <div class="grid md:grid-cols-2 gap-4">
      <BlockchainAccountSelector
        v-model="selectedAccounts"
        :chains="chains"
        :usable-addresses="addresses"
        flat
        dense
        outlined
        no-padding
      />
      <LiquidityPoolSelector
        v-model="selectedPools"
        :pools="poolAssets"
        :type="lpType"
        flat
        dense
        outlined
        no-padding
      />
    </div>

    <PaginatedCards :identifier="getIdentifier" :items="balances">
      <template #item="{ item }">
        <UniswapPoolBalances :item="item" :lp-type="lpType" />
      </template>
    </PaginatedCards>

    <UniswapDetails
      v-if="premium"
      :loading="secondaryRefreshing"
      :profit="poolProfit"
      :selected-accounts="selectedAccounts"
    />
  </div>
</template>
