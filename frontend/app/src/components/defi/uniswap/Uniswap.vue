<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('uniswap.loading') }}
    </template>
  </progress-screen>
  <v-container v-else class="uniswap">
    <refresh-header
      :title="$t('uniswap.title')"
      :loading="anyRefreshing"
      @refresh="refresh()"
    />
    <blockchain-account-selector
      v-model="selectedAccount"
      class="mt-4"
      hint
      :chains="[ETH]"
      :usable-addresses="uniswapAddresses"
    />
    <v-row class="mt-4">
      <v-col
        v-for="entry in balances"
        :key="entry.poolAddress"
        cols="12"
        sm="6"
        lg="6"
        xl="4"
      >
        <v-card>
          <v-card-text>
            <v-row align="center">
              <v-col cols="auto">
                <uniswap-pool-asset
                  :assets="entry.assets.map(value => assetName(value.asset))"
                />
              </v-col>
              <v-col>
                <div class="text-h4">
                  {{
                    $t('uniswap.pool_header', {
                      asset1: assetName(entry.assets[0].asset),
                      asset2: assetName(entry.assets[1].asset)
                    })
                  }}
                </div>
                <v-row no-gutters align="center">
                  <v-col cols="auto">
                    <hash-link :text="entry.poolAddress" />
                  </v-col>
                </v-row>
              </v-col>
            </v-row>
            <v-row class="mt-2">
              <v-col class="d-flex flex-column">
                <span
                  :class="'text-end'"
                  class="text--secondary text-body-1"
                  v-text="$t('uniswap.balance')"
                />
                <balance-display
                  class="text-h4 mt-1 text uniswap__amount"
                  :value="entry.userBalance"
                  no-icon
                  :min-width="0"
                  asset=""
                  :asset-padding="0"
                />
              </v-col>
            </v-row>

            <v-divider />

            <v-row
              v-for="asset in entry.assets"
              :key="`${assetName(asset.asset)}-${entry.poolAddress}-balances`"
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

            <v-divider />

            <v-row v-if="!!entry.totalSupply" no-gutters class="mt-2 mb-1">
              <v-col>
                <span
                  class="text--secondary"
                  v-text="$t('uniswap.liquidity')"
                />
                <amount-display
                  class="font-weight-medium ms-2"
                  :value="entry.totalSupply"
                  :asset-padding="0"
                />
              </v-col>
            </v-row>

            <v-row
              v-for="asset in entry.assets"
              :key="`${assetName(asset.asset)}-${entry.poolAddress}-details`"
              no-gutters
            >
              <v-col
                v-if="!!asset.totalAmount"
                cols="auto"
                class="text--secondary"
                v-text="
                  $t('uniswap.asset_supply', { asset: assetName(asset.asset) })
                "
              />
              <v-col
                v-if="!!asset.totalAmount"
                class="font-weight-medium d-flex ms-3"
                cols="auto"
              >
                <amount-display :value="asset.totalAmount" />
              </v-col>
              <v-col cols="auto">
                <i18n
                  tag="div"
                  path="uniswap.asset_price"
                  class="text--secondary ms-2"
                  :places="{ asset: assetName(asset.asset) }"
                >
                  <amount-display
                    class="font-weight-medium"
                    :value="asset.usdPrice"
                    show-currency="symbol"
                    fiat-currency="USD"
                  />
                </i18n>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <uniswap-details
      :loading="secondaryLoading"
      :selected-addresses="selectedAddresses"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import UniswapPoolAsset from '@/components/display/icons/UniswapPoolAsset.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
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
export default class Uniswap extends Mixins(StatusMixin) {
  readonly ETH = ETH;
  readonly assetName = assetName;
  section = Section.DEFI_UNISWAP_BALANCES;
  secondSection = Section.DEFI_UNISWAP_EVENTS;

  assetInfo!: (asset: string) => SupportedAsset | undefined;
  uniswapBalances!: (addresses: string[]) => UniswapBalance[];
  uniswapAddresses!: string[];
  selectedAccount: GeneralAccount | null = null;
  fetchUniswapBalances!: (refresh: boolean) => Promise<void>;
  fetchUniswapEvents!: (refresh: boolean) => Promise<void>;

  get selectedAddresses(): string[] {
    return this.selectedAccount ? [this.selectedAccount.address] : [];
  }

  get balances(): UniswapBalance[] {
    return this.uniswapBalances(this.selectedAddresses);
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
  &__amount {
    font-size: 27px !important;
  }

  &__asset-details {
    width: 100%;
  }
}
</style>
