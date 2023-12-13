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

const getIdentifier = (item: XswapBalance) => item.address;

const lpType = LpType.UNISWAP_V2;

const refresh = async (ignoreCache: boolean = false) => {
  await Promise.all([fetchBalances(ignoreCache), fetchEvents(ignoreCache)]);
};

onMounted(async () => {
  await refresh();
});

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t(
      'navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v2'
    ).toLocaleLowerCase()
  })
);
</script>

<template>
  <ModuleNotActive v-if="!enabled" :modules="modules" />
  <ProgressScreen v-else-if="loading">
    <template #message>
      {{ t('uniswap.loading') }}
    </template>
    <template v-if="!premium" #default>
      <i18n tag="div" path="uniswap.loading_non_premium">
        <ExternalLink :text="t('uniswap.premium')" premium />
      </i18n>
    </template>
  </ProgressScreen>
  <TablePageLayout
    v-else
    :title="[
      t('navigation_menu.defi'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v2')
    ]"
  >
    <template #buttons>
      <div class="flex items-center gap-4">
        <ActiveModules :modules="modules" />

        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              :loading="primaryRefreshing || secondaryRefreshing"
              @click="refresh(true)"
            >
              <template #prepend>
                <RuiIcon name="refresh-line" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ refreshTooltip }}
        </RuiTooltip>
      </div>
    </template>
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

    <PaginatedCards
      v-if="balances.length > 0"
      :identifier="getIdentifier"
      :items="balances"
    >
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
  </TablePageLayout>
</template>
