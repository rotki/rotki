<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { LpType } from '@rotki/common/lib/defi';
import {
  type XswapAsset,
  type XswapBalance
} from '@rotki/common/lib/defi/xswap';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

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
const { tokenAddress } = useAssetInfoRetrieval();
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

const { dark } = useTheme();

const refresh = async () => {
  await fetchBalances(true);
};

const getAssets = (assets: XswapAsset[]) => assets.map(({ asset }) => asset);

onMounted(async () => {
  await fetchBalances(false);
});

const { getPoolName } = useLiquidityPosition();
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
  <div v-else class="uniswap">
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
          <LpPoolHeader>
            <template #icon>
              <LpPoolIcon :assets="getAssets(item.assets)" :type="lpType" />
            </template>
            <template #name>
              {{ getPoolName(lpType, getAssets(item.assets)) }}
            </template>
            <template #hash>
              <HashLink :text="item.address" />
            </template>
            <template #detail>
              <UniswapPoolDetails :balance="item" />
            </template>
          </LpPoolHeader>

          <div class="mt-6">
            <NftDetails v-if="item.nftId" :identifier="item.nftId" />

            <div class="d-flex flex-wrap">
              <div class="mt-6 mr-16">
                <div class="text-rui-text-secondary text-body-2">
                  {{ t('common.balance') }}
                </div>
                <div class="d-flex text-h6">
                  <AmountDisplay
                    :value="item.userBalance.usdValue"
                    fiat-currency="USD"
                  />
                </div>
              </div>
              <div
                v-if="item.priceRange && item.priceRange.length > 0"
                class="mt-6"
                :class="$style['price-range']"
              >
                <div class="text-rui-text-secondary text-body-2">
                  {{ t('uniswap.price_range') }}
                </div>
                <div class="d-flex text-h6">
                  <AmountDisplay
                    :value="item.priceRange[0]"
                    fiat-currency="USD"
                  />
                  <div class="px-2">-</div>
                  <AmountDisplay
                    :value="item.priceRange[1]"
                    fiat-currency="USD"
                  />
                </div>
              </div>
            </div>

            <div class="mt-6">
              <div class="text-rui-text-secondary text-body-2">
                {{ t('common.assets') }}
              </div>
              <div v-if="premium">
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

              <div v-else class="pt-4 d-flex align-center">
                <VAvatar rounded :color="dark ? 'white' : 'grey lighten-3'">
                  <VIcon>mdi-lock</VIcon>
                </VAvatar>
                <div class="ml-4">
                  <i18n tag="div" path="uniswap.assets_non_premium">
                    <BaseExternalLink
                      :text="t('uniswap.premium')"
                      :href="premiumURL"
                    />
                  </i18n>
                </div>
              </div>
            </div>
          </div>
        </Card>
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

<style module lang="scss">
.price-range {
  min-width: 50%;
}
</style>
