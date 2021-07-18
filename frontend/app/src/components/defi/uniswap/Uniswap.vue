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
  <v-container v-else class="uniswap">
    <refresh-header
      :title="$t('uniswap.title')"
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
    <v-row class="mt-4">
      <v-col
        v-for="entry in balances"
        :key="entry.poolAddress"
        cols="12"
        sm="6"
        lg="6"
        xl="4"
      >
        <card>
          <template #title>
            {{
              $t('uniswap.pool_header', {
                asset1: getSymbol(entry.assets[0].asset),
                asset2: getSymbol(entry.assets[1].asset)
              })
            }}
          </template>
          <template #details>
            <uniswap-pool-details :balance="entry" />
          </template>
          <template #subtitle>
            <hash-link :text="entry.poolAddress" />
          </template>
          <template #icon>
            <uniswap-pool-asset
              :assets="entry.assets.map(({ asset }) => asset)"
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
                :value="entry.userBalance"
                no-icon
                :min-width="0"
                asset=""
                :asset-padding="0"
              />
            </v-col>
          </v-row>

          <v-row
            v-for="asset in entry.assets"
            :key="`${asset.asset}-${entry.poolAddress}-balances`"
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
      </v-col>
    </v-row>
    <uniswap-details
      v-if="premium"
      :loading="secondaryLoading"
      :selected-addresses="selectedAddresses"
      :selected-pool-address="selectedPools"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
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
import { MODULE_UNISWAP } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';
import { Section } from '@/store/const';
import { UniswapBalance } from '@/store/defi/types';
import { ETH, GeneralAccount } from '@/typing/types';

@Component({
  components: {
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
  readonly ETH = ETH;
  readonly modules: SupportedModules[] = [MODULE_UNISWAP];
  section = Section.DEFI_UNISWAP_BALANCES;
  secondSection = Section.DEFI_UNISWAP_EVENTS;

  uniswapBalances!: (addresses: string[]) => UniswapBalance[];
  uniswapAddresses!: string[];
  selectedAccount: GeneralAccount | null = null;
  selectedPools: string[] = [];
  fetchUniswapBalances!: (refresh: boolean) => Promise<void>;
  fetchUniswapEvents!: (refresh: boolean) => Promise<void>;

  get isEnabled(): boolean {
    return this.isModuleEnabled(MODULE_UNISWAP);
  }

  get selectedAddresses(): string[] {
    return this.selectedAccount ? [this.selectedAccount.address] : [];
  }

  get balances(): UniswapBalance[] {
    const balances = this.uniswapBalances(this.selectedAddresses);
    if (this.selectedPools.length === 0) {
      return balances;
    }
    return balances.filter(({ poolAddress }) =>
      this.selectedPools.includes(poolAddress)
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
