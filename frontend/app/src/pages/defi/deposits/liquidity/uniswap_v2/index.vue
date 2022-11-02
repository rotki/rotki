<template>
  <module-not-active v-if="!enabled" :modules="modules" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ tc('uniswap.loading') }}
    </template>
    <template v-if="!premium" #default>
      <i18n tag="div" path="uniswap.loading_non_premium">
        <base-external-link :text="tc('uniswap.premium')" :href="premiumURL" />
      </i18n>
    </template>
  </progress-screen>
  <div v-else class="uniswap">
    <refresh-header
      :title="tc('uniswap.title', 0, { v: 2 })"
      class="mt-4"
      :loading="primaryRefreshing || secondaryRefreshing"
      @refresh="refresh()"
    >
      <template #actions>
        <active-modules :modules="modules" />
      </template>
    </refresh-header>
    <v-row class="mt-4">
      <v-col>
        <blockchain-account-selector
          v-model="selectedAccount"
          :chains="chains"
          :usable-addresses="addresses"
          flat
          dense
          outlined
          no-padding
        />
      </v-col>
      <v-col>
        <liquidity-pool-selector
          v-model="selectedPools"
          :pools="poolAssets"
          :type="lpType"
          flat
          dense
          outlined
          no-padding
        />
      </v-col>
    </v-row>
    <paginated-cards :identifier="getIdentifier" :items="balances" class="mt-4">
      <template #item="{ item }">
        <card>
          <template v-if="item.assets.length > 0" #title>
            {{ getPoolName(lpType, getAssets(item.assets)) }}
          </template>
          <template #details>
            <uniswap-pool-details :balance="item" />
          </template>
          <template #subtitle>
            <hash-link :text="item.address" />
          </template>
          <template #icon>
            <lp-pool-icon :assets="getAssets(item.assets)" :type="lpType" />
          </template>

          <div class="mt-2">
            <div>
              <div class="text--secondary text-body-2">
                {{ tc('common.balance') }}
              </div>
              <div class="d-flex text-h6">
                <balance-display
                  :value="item.userBalance"
                  align="start"
                  no-icon
                  asset=""
                />
              </div>
            </div>

            <div class="mt-6">
              <div class="text--secondary text-body-2">
                {{ tc('common.assets') }}
              </div>
              <div>
                <v-row
                  v-for="asset in item.assets"
                  :key="`${asset.asset}-${item.address}-balances`"
                  align="center"
                  no-gutters
                  class="mt-2"
                >
                  <v-col cols="auto">
                    <asset-icon :identifier="asset.asset" size="32px" />
                  </v-col>
                  <v-col class="d-flex ml-4" cols="auto">
                    <div class="mr-4">
                      <balance-display
                        no-icon
                        align="start"
                        :asset="asset.asset"
                        :value="asset.userBalance"
                      />
                    </div>
                    <hash-link
                      link-only
                      :text="tokenAddress(asset.asset).value"
                    />
                  </v-col>
                </v-row>
              </div>
            </div>
          </div>
        </card>
      </template>
    </paginated-cards>

    <uniswap-details
      v-if="premium"
      :loading="secondaryRefreshing"
      :events="events"
      :profit="poolProfit"
    />
  </div>
</template>

<script setup lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { LpType } from '@rotki/common/lib/defi';
import { XswapAsset, XswapBalance } from '@rotki/common/lib/defi/xswap';
import { ComputedRef } from 'vue';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import PaginatedCards from '@/components/common/PaginatedCards.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import UniswapPoolDetails from '@/components/defi/uniswap/UniswapPoolDetails.vue';
import LpPoolIcon from '@/components/display/defi/LpPoolIcon.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { useSectionLoading } from '@/composables/common';
import { setupLiquidityPosition } from '@/composables/defi';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useInterop } from '@/electron-interop';
import { UniswapDetails } from '@/premium/premium';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useUniswapStore } from '@/store/defi/uniswap';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const modules = [Module.UNISWAP];
const chains = [Blockchain.ETH];

const selectedAccount = ref<GeneralAccount | null>(null);
const selectedPools = ref<string[]>([]);

const store = useUniswapStore();

const {
  fetchEvents,
  fetchV2Balances: fetchBalances,
  uniswapV2Balances: uniswapBalances,
  uniswapEvents,
  uniswapPoolProfit
} = store;

const { uniswapV2Addresses: addresses, uniswapV2PoolAssets: poolAssets } =
  storeToRefs(store);

const { isModuleEnabled } = useModules();
const { tokenAddress } = useAssetInfoRetrieval();
const { isSectionRefreshing, shouldShowLoadingScreen } = useSectionLoading();

const { tc } = useI18n();
const { premiumURL } = useInterop();

const enabled = isModuleEnabled(modules[0]);
const loading = shouldShowLoadingScreen(Section.DEFI_UNISWAP_V2_BALANCES);
const primaryRefreshing = isSectionRefreshing(Section.DEFI_UNISWAP_V2_BALANCES);
const secondaryRefreshing = isSectionRefreshing(Section.DEFI_UNISWAP_EVENTS);
const premium = usePremium();

const selectedAddresses = computed(() => {
  let account = get(selectedAccount);
  return account ? [account.address] : [];
});

const balances: ComputedRef<XswapBalance[]> = computed(() => {
  const addresses = get(selectedAddresses);
  const pools = get(selectedPools);
  const balances = get(uniswapBalances(addresses));
  return pools.length === 0
    ? balances
    : balances.filter(({ address }) => pools.includes(address));
});

const events = computed(() => {
  const addresses = get(selectedAddresses);
  const pools = get(selectedPools);
  const events = get(uniswapEvents(addresses));
  return pools.length === 0
    ? events
    : events.filter(({ address }) => pools.includes(address));
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

const getIdentifier = (item: XswapBalance) => {
  return item.address;
};

const getAssets = (assets: XswapAsset[]) => {
  return assets.map(({ asset }) => asset);
};

onMounted(async () => {
  await Promise.all([fetchBalances(false), fetchEvents(false)]);
});

const { getPoolName } = setupLiquidityPosition();
const lpType = LpType.UNISWAP_V2;
</script>
