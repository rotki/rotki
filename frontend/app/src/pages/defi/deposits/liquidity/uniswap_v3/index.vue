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

const { premiumURL } = useInterop();

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

const refresh = async () => {
  await fetchBalances(true);
};

onMounted(async () => {
  await fetchBalances(false);
});

const lpType = LpType.UNISWAP_V3;

const getIdentifier = (item: XswapBalance) => item.nftId;
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
      :title="t('uniswap.title', { v: 3 })"
      class="mt-4"
      :loading="primaryRefreshing || secondaryRefreshing"
      @refresh="refresh()"
    >
      <template #actions>
        <ActiveModules :modules="modules" />
      </template>
    </RefreshHeader>

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

    <PaginatedCards :identifier="getIdentifier" :items="balances">
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
  </div>
</template>
