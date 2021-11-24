<template>
  <module-not-active v-if="!isEnabled" :modules="modules" />
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
      :loading="anyRefreshing"
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
          hint
          :chains="[ETH]"
          :usable-addresses="uniswapAddresses"
        />
      </v-col>
      <v-col>
        <uniswap-pool-filter v-model="selectedPools" />
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
                :min-width="0"
                asset=""
                :asset-padding="0"
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
              <asset-icon
                :identifier="asset.asset"
                :symbol="getSymbol(asset.asset)"
                size="32px"
              />
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
      :loading="secondaryLoading"
      :selected-addresses="selectedAddresses"
      :selected-pool-address="selectedPools"
    />
  </div>
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { XswapBalance } from '@rotki/common/lib/defi/xswap';
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import PaginatedCards from '@/components/common/PaginatedCards.vue';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import UniswapPoolDetails from '@/components/defi/uniswap/UniswapPoolDetails.vue';
import UniswapPoolFilter from '@/components/defi/uniswap/UniswapPoolFilter.vue';
import UniswapPoolAsset from '@/components/display/icons/UniswapPoolAsset.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import AssetMixin from '@/mixins/asset-mixin';
import ModuleMixin from '@/mixins/module-mixin';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { UniswapDetails } from '@/premium/premium';
import { Section } from '@/store/const';
import { Module } from '@/types/modules';

@Component({
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
  computed: {
    ...mapGetters('defi', ['uniswapBalances', 'uniswapAddresses'])
  },
  methods: {
    ...mapActions('defi', ['fetchUniswapEvents', 'fetchUniswapBalances'])
  }
})
export default class Uniswap extends Mixins(
  StatusMixin,
  ModuleMixin,
  PremiumMixin,
  AssetMixin
) {
  readonly ETH = Blockchain.ETH;
  readonly modules: Module[] = [Module.UNISWAP];
  section = Section.DEFI_UNISWAP_BALANCES;
  secondSection = Section.DEFI_UNISWAP_EVENTS;

  uniswapBalances!: (addresses: string[]) => XswapBalance[];
  uniswapAddresses!: string[];
  selectedAccount: GeneralAccount | null = null;
  selectedPools: string[] = [];
  fetchUniswapBalances!: (refresh: boolean) => Promise<void>;
  fetchUniswapEvents!: (refresh: boolean) => Promise<void>;

  get isEnabled(): boolean {
    return this.isModuleEnabled(Module.UNISWAP);
  }

  get selectedAddresses(): string[] {
    return this.selectedAccount ? [this.selectedAccount.address] : [];
  }

  get balances(): XswapBalance[] {
    const balances = this.uniswapBalances(this.selectedAddresses);
    if (this.selectedPools.length === 0) {
      return balances;
    }
    return balances.filter(({ address }) =>
      this.selectedPools.includes(address)
    );
  }

  async mounted() {
    await Promise.all([
      this.fetchUniswapBalances(false),
      this.fetchUniswapEvents(false)
    ]);
  }

  async refresh() {
    await Promise.all([
      this.fetchUniswapBalances(true),
      this.fetchUniswapEvents(true)
    ]);
  }
}
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
