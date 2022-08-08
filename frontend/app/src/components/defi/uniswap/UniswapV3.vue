<template>
  <module-not-active v-if="!enabled" :modules="modules" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ $t('uniswap.loading') }}
    </template>
    <template v-if="!premium" #default>
      <i18n tag="div" path="uniswap.loading_non_premium">
        <base-external-link
          :text="$t('uniswap.premium')"
          :href="$interop.premiumURL"
        />
      </i18n>
    </template>
  </progress-screen>
  <div v-else class="uniswap">
    <refresh-header
      :title="$t('uniswap.title', { v: 3 })"
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
        <uniswap-pool-filter
          v-model="selectedPools"
          :pool-assets="poolAssets"
          version="3"
          flat
          dense
          outlined
          no-padding
        />
      </v-col>
    </v-row>
    <paginated-cards
      :identifier="item => item.nftId"
      :items="balances"
      class="mt-4"
    >
      <template #item="{ item }">
        <card>
          <template v-if="item.assets.length > 0" #title>
            {{
              $t('uniswap.pool_header', {
                version: '3',
                asset1: getSymbol(item.assets[0].asset),
                asset2: getSymbol(item.assets[1].asset)
              })
            }}
          </template>
          <template #details>
            <uniswap-pool-details :balance="item" />
          </template>
          <template #subtitle>
            <hash-link :text="item.address" />
          </template>
          <template #icon>
            <uniswap-pool-asset
              :assets="item.assets.map(({ asset }) => asset)"
            />
          </template>

          <div>
            <nft-details
              v-if="item.nftId"
              class="mt-4"
              :identifier="item.nftId"
            />

            <div class="d-flex flex-wrap">
              <div class="mt-6 mr-16">
                <div class="text--secondary text-body-2">
                  {{ $t('common.balance') }}
                </div>
                <div class="d-flex text-h6">
                  <amount-display
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
                <div class="text--secondary text-body-2">
                  {{ $t('uniswap.price_range') }}
                </div>
                <div class="d-flex text-h6">
                  <amount-display
                    :value="item.priceRange[0]"
                    fiat-currency="USD"
                  />
                  <div class="px-2">-</div>
                  <amount-display
                    :value="item.priceRange[1]"
                    fiat-currency="USD"
                  />
                </div>
              </div>
            </div>

            <div class="mt-6">
              <div class="text--secondary text-body-2">
                {{ $t('common.assets') }}
              </div>
              <div v-if="premium">
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
                    <hash-link link-only :text="getTokenAddress(asset.asset)" />
                  </v-col>
                </v-row>
              </div>
              <div v-else class="pt-4 d-flex align-center">
                <v-avatar rounded :color="dark ? 'white' : 'grey lighten-3'">
                  <v-icon>mdi-lock</v-icon>
                </v-avatar>
                <div class="ml-4">
                  <i18n tag="div" path="uniswap.assets_non_premium">
                    <base-external-link
                      :text="$t('uniswap.premium')"
                      :href="$interop.premiumURL"
                    />
                  </i18n>
                </div>
              </div>
            </div>
          </div>
        </card>
      </template>
    </paginated-cards>
  </div>
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  onMounted,
  ref
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import PaginatedCards from '@/components/common/PaginatedCards.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import UniswapPoolDetails from '@/components/defi/uniswap/UniswapPoolDetails.vue';
import UniswapPoolFilter from '@/components/defi/uniswap/UniswapPoolFilter.vue';
import UniswapPoolAsset from '@/components/display/icons/UniswapPoolAsset.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import NftDetails from '@/components/helper/NftDetails.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking, useTheme } from '@/composables/common';
import { getPremium, useModules } from '@/composables/session';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section } from '@/store/const';
import { useUniswapStore } from '@/store/defi/uniswap';
import { Module } from '@/types/modules';

export default defineComponent({
  components: {
    NftDetails,
    PaginatedCards,
    ActiveModules,
    UniswapPoolDetails,
    UniswapPoolFilter,
    BaseExternalLink,
    ModuleNotActive,
    ProgressScreen,
    UniswapPoolAsset,
    BlockchainAccountSelector
  },
  setup() {
    const selectedAccount = ref<GeneralAccount | null>(null);
    const selectedPools = ref<string[]>([]);
    const {
      fetchV3Balances: fetchBalances,
      uniswapV3Addresses: addresses,
      uniswapV3Balances: uniswapBalances,
      uniswapV3PoolAssets: poolAssets
    } = useUniswapStore();
    const { isModuleEnabled } = useModules();
    const { getAssetSymbol: getSymbol, getTokenAddress } =
      useAssetInfoRetrieval();
    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const loading = shouldShowLoadingScreen(Section.DEFI_UNISWAP_V3_BALANCES);
    const primaryRefreshing = isSectionRefreshing(
      Section.DEFI_UNISWAP_V3_BALANCES
    );
    const secondaryRefreshing = isSectionRefreshing(
      Section.DEFI_UNISWAP_EVENTS
    );

    const selectedAddresses = computed(() => {
      let account = get(selectedAccount);
      return account ? [account.address] : [];
    });

    const balances = computed(() => {
      const addresses = get(selectedAddresses);
      const pools = get(selectedPools);
      const balances = get(uniswapBalances(addresses));

      return pools.length === 0
        ? balances
        : balances.filter(({ address }) => pools.includes(address));
    });

    onMounted(async () => {
      await fetchBalances(false);
    });

    const refresh = async () => {
      await fetchBalances(true);
    };

    const uniswap = Module.UNISWAP;

    const premium = getPremium();

    const { dark } = useTheme();

    return {
      dark,
      premium,
      selectedAccount,
      selectedPools,
      selectedAddresses,
      addresses,
      balances,
      poolAssets,
      loading,
      primaryRefreshing,
      secondaryRefreshing,
      chains: [Blockchain.ETH],
      modules: [uniswap],
      enabled: isModuleEnabled(uniswap),
      refresh,
      getSymbol,
      getTokenAddress
    };
  }
});
</script>

<style module lang="scss">
.price-range {
  min-width: 50%;
}
</style>
