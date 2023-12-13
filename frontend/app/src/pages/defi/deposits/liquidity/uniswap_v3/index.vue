<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { LpType } from '@rotki/common/lib/defi';
import { type XswapBalance } from '@rotki/common/lib/defi/xswap';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import Uniswap3PoolBalances from '@/components/defi/uniswap/Uniswap3PoolBalances.vue';

const uniswap = Module.UNISWAP;
const chains = [Blockchain.ETH];
const modules = [uniswap];

const selectedAccounts = ref<GeneralAccount[]>([]);
const selectedPools = ref<string[]>([]);

const store = useUniswapStore();

const { fetchV3Balances: fetchBalances, uniswapV3Balances: uniswapBalances } =
  store;

const { uniswapV3Addresses: addresses, uniswapV3PoolAssets: poolAssets } =
  storeToRefs(store);
const { isModuleEnabled } = useModules();
const { isLoading, shouldShowLoadingScreen } = useStatusStore();
const { t } = useI18n();

const enabled = isModuleEnabled(uniswap);
const loading = shouldShowLoadingScreen(Section.DEFI_UNISWAP_V3_BALANCES);
const primaryRefreshing = isLoading(Section.DEFI_UNISWAP_V3_BALANCES);
const secondaryRefreshing = isLoading(Section.DEFI_UNISWAP_EVENTS);

const selectedAddresses = useArrayMap(selectedAccounts, a => a.address);

const balances = computed(() => {
  const addresses = get(selectedAddresses);
  const pools = get(selectedPools);
  const balances = get(uniswapBalances(addresses));

  return pools.length === 0
    ? balances
    : balances.filter(({ address }) => pools.includes(address));
});

const premium = usePremium();

const lpType = LpType.UNISWAP_V3;

const getIdentifier = (item: XswapBalance) => item.nftId || '';

const refresh = async (ignoreCache: boolean = false) => {
  await fetchBalances(ignoreCache);
};

onMounted(async () => {
  await refresh();
});

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t(
      'navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v3'
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
      <i18n path="uniswap.loading_non_premium">
        <ExternalLink :text="t('uniswap.premium')" color="primary" premium />
      </i18n>
    </template>
  </ProgressScreen>
  <TablePageLayout
    v-else
    :title="[
      t('navigation_menu.defi'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity'),
      t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v3')
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
    <div class="grid grid-cols-2 gap-4">
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
        <Uniswap3PoolBalances :item="item" :lp-type="lpType" />
      </template>
    </PaginatedCards>

    <HistoryEventsView
      use-external-account-filter
      :section-title="t('common.events')"
      :protocols="['uniswap-v3']"
      :external-account-filter="selectedAccounts"
      :only-chains="chains"
      :entry-types="[HistoryEventEntryType.EVM_EVENT]"
    />
  </TablePageLayout>
</template>
