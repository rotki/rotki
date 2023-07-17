<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { LpType } from '@rotki/common/lib/defi';
import {
  type XswapAsset,
  type XswapBalance
} from '@rotki/common/lib/defi/xswap';
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
const { tokenAddress } = useAssetInfoRetrieval();
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

const getAssets = (assets: XswapAsset[]) => assets.map(({ asset }) => asset);

onMounted(async () => {
  await Promise.all([fetchBalances(false), fetchEvents(false)]);
});

const { getPoolName } = useLiquidityPosition();
const lpType = LpType.UNISWAP_V2;
</script>

<template>
  <ModuleNotActive v-if="!enabled" :modules="modules" />
  <ProgressScreen v-else-if="loading">
    <template #message>
      {{ t('uniswap.loading') }}
    </template>
    <template v-if="!premium" #default>
      <I18n tag="div" path="uniswap.loading_non_premium">
        <BaseExternalLink :text="t('uniswap.premium')" :href="premiumURL" />
      </I18n>
    </template>
  </ProgressScreen>
  <div v-else class="uniswap">
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
    <VRow class="mt-4">
      <VCol>
        <BlockchainAccountSelector
          v-model="selectedAccounts"
          :chains="chains"
          :usable-addresses="addresses"
          flat
          dense
          outlined
          no-padding
        />
      </VCol>
      <VCol>
        <LiquidityPoolSelector
          v-model="selectedPools"
          :pools="poolAssets"
          :type="lpType"
          flat
          dense
          outlined
          no-padding
        />
      </VCol>
    </VRow>
    <PaginatedCards :identifier="getIdentifier" :items="balances" class="mt-4">
      <template #item="{ item }">
        <Card>
          <template v-if="item.assets.length > 0" #title>
            {{ getPoolName(lpType, getAssets(item.assets)) }}
          </template>
          <template #details>
            <UniswapPoolDetails :balance="item" />
          </template>
          <template #subtitle>
            <HashLink :text="item.address" />
          </template>
          <template #icon>
            <LpPoolIcon :assets="getAssets(item.assets)" :type="lpType" />
          </template>

          <div class="mt-2">
            <div>
              <div class="text--secondary text-body-2">
                {{ t('common.balance') }}
              </div>
              <div class="d-flex text-h6">
                <BalanceDisplay
                  :value="item.userBalance"
                  align="start"
                  no-icon
                  asset=""
                />
              </div>
            </div>

            <div class="mt-6">
              <div class="text--secondary text-body-2">
                {{ t('common.assets') }}
              </div>
              <div>
                <VRow
                  v-for="asset in item.assets"
                  :key="`${asset.asset}-${item.address}-balances`"
                  align="center"
                  no-gutters
                  class="mt-2"
                >
                  <VCol cols="auto">
                    <AssetIcon :identifier="asset.asset" size="32px" />
                  </VCol>
                  <VCol class="d-flex ml-4" cols="auto">
                    <div class="mr-4">
                      <BalanceDisplay
                        no-icon
                        align="start"
                        :asset="asset.asset"
                        :value="asset.userBalance"
                      />
                    </div>
                    <HashLink
                      link-only
                      :text="tokenAddress(asset.asset).value"
                    />
                  </VCol>
                </VRow>
              </div>
            </div>
          </div>
        </Card>
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
