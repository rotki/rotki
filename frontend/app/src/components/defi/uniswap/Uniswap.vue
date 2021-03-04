<template>
  <module-not-active v-if="!isUniswapEnabled" :module="MODULE_UNISWAP" />
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
    />
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
                asset1: assetName(entry.assets[0].asset),
                asset2: assetName(entry.assets[1].asset)
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
              :assets="entry.assets.map(value => assetName(value.asset))"
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
            :key="`${assetName(asset.asset)}-${entry.poolAddress}-balances`"
            class="uniswap__tokens"
            align="center"
            justify="end"
          >
            <v-col cols="auto">
              <crypto-icon :symbol="assetName(asset.asset)" size="32px" />
            </v-col>
            <v-col class="d-flex" cols="auto">
              <div>
                <balance-display
                  no-icon
                  :asset="assetName(asset.asset)"
                  :value="asset.userBalance"
                />
              </div>
              <hash-link link-only :text="assetAddress(asset.asset)" />
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
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import UniswapPoolDetails from '@/components/defi/uniswap/UniswapPoolDetails.vue';
import UniswapPoolFilter from '@/components/defi/uniswap/UniswapPoolFilter.vue';
import UniswapPoolAsset from '@/components/display/icons/UniswapPoolAsset.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import DefiModuleMixin from '@/mixins/defi-module-mixin';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { UnknownToken } from '@/services/defi/types';
import { SupportedAsset } from '@/services/types-model';
import { Section } from '@/store/const';
import { UniswapBalance } from '@/store/defi/types';
import { assetName } from '@/store/defi/utils';
import { ETH, GeneralAccount } from '@/typing/types';
import { UniswapDetails } from '@/utils/premium';

@Component({
  components: {
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
    ...mapGetters('balances', ['assetInfo']),
    ...mapGetters('defi', ['uniswapBalances', 'uniswapAddresses'])
  },
  methods: {
    ...mapActions('defi', ['fetchUniswapEvents', 'fetchUniswapBalances'])
  }
})
export default class Uniswap extends Mixins(
  StatusMixin,
  DefiModuleMixin,
  PremiumMixin
) {
  readonly ETH = ETH;
  readonly assetName = assetName;
  section = Section.DEFI_UNISWAP_BALANCES;
  secondSection = Section.DEFI_UNISWAP_EVENTS;

  assetInfo!: (asset: string) => SupportedAsset | undefined;
  uniswapBalances!: (addresses: string[]) => UniswapBalance[];
  uniswapAddresses!: string[];
  selectedAccount: GeneralAccount | null = null;
  selectedPools: string[] = [];
  fetchUniswapBalances!: (refresh: boolean) => Promise<void>;
  fetchUniswapEvents!: (refresh: boolean) => Promise<void>;

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

  assetAddress(asset: UnknownToken | string) {
    if (typeof asset === 'string') {
      return this.assetInfo(asset)?.ethereumAddress ?? '';
    }
    return asset.ethereumAddress;
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
