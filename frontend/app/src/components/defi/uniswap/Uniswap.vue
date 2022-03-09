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
      :title="$t('uniswap.title')"
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
          flat
          dense
          outlined
          no-padding
        />
      </v-col>
    </v-row>
    <paginated-cards
      :identifier="item => item.address"
      :items="balances"
      class="mt-4"
    >
      <template #item="{ item }">
        <card>
          <template #title>
            {{
              $t('uniswap.pool_header', {
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
          <v-row align="center">
            <v-col cols="auto">
              <span class="font-weight-medium text-body-1">
                {{ $t('uniswap.balance') }}
              </span>
            </v-col>
            <v-col class="d-flex flex-column">
              <balance-display
                class="text-h5 mt-1 text"
                :value="item.userBalance"
                no-icon
                asset=""
              />
            </v-col>
          </v-row>

          <v-row
            v-for="asset in item.assets"
            :key="`${asset.asset}-${item.address}-balances`"
            class="uniswap__tokens"
            align="center"
            justify="end"
          >
            <v-col cols="auto">
              <asset-icon :identifier="asset.asset" size="32px" />
            </v-col>
            <v-col class="d-flex" cols="auto">
              <div>
                <balance-display
                  no-icon
                  :asset="asset.asset"
                  :value="asset.userBalance"
                />
              </div>
              <hash-link link-only :text="getTokenAddress(asset.asset)" />
            </v-col>
          </v-row>
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
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import { getPremium, setupModuleEnabled } from '@/composables/session';
import { UniswapDetails } from '@/premium/premium';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section } from '@/store/const';
import { useUniswap } from '@/store/defi/uniswap';
import { Module } from '@/types/modules';

export default defineComponent({
  components: {
    PaginatedCards,
    ActiveModules,
    UniswapPoolDetails,
    UniswapPoolFilter,
    BaseExternalLink,
    ModuleNotActive,
    UniswapDetails,
    ProgressScreen,
    UniswapPoolAsset,
    BlockchainAccountSelector
  },
  setup() {
    const selectedAccount = ref<GeneralAccount | null>(null);
    const selectedPools = ref<string[]>([]);
    const {
      fetchEvents,
      fetchBalances,
      addresses,
      uniswapBalances,
      uniswapEvents,
      uniswapPoolProfit
    } = useUniswap();
    const { isModuleEnabled } = setupModuleEnabled();
    const { getAssetSymbol: getSymbol, getTokenAddress } =
      useAssetInfoRetrieval();
    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const loading = shouldShowLoadingScreen(Section.DEFI_UNISWAP_BALANCES);
    const primaryRefreshing = isSectionRefreshing(
      Section.DEFI_UNISWAP_BALANCES
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

    onMounted(async () => {
      await Promise.all([fetchBalances(false), fetchEvents(false)]);
    });

    const refresh = async () => {
      await Promise.all([fetchBalances(true), fetchEvents(true)]);
    };

    const uniswap = Module.UNISWAP;
    return {
      selectedAccount,
      selectedPools,
      selectedAddresses,
      addresses,
      balances,
      events,
      poolProfit,
      loading,
      primaryRefreshing,
      secondaryRefreshing,
      premium: getPremium(),
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

<style scoped lang="scss">
.uniswap {
  &__asset-details {
    width: 100%;
  }

  &__tokens {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
  }
}
</style>
