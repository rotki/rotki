<template>
  <v-card class="exchange-balances mt-8">
    <v-card-title v-text="$t('exchange_balances.title')" />
    <v-card-text>
      <v-btn
        absolute
        fab
        top
        right
        dark
        color="primary"
        to="/settings/api-keys/exchanges"
      >
        <v-icon>
          mdi-plus
        </v-icon>
      </v-btn>
      <v-row
        v-if="connectedExchanges.length > 0"
        no-gutters
        class="exchange-balances__content"
      >
        <v-col cols="12" class="hidden-md-and-up">
          <v-select
            v-model="selectedExchange"
            filled
            :items="connectedExchanges"
            hide-details
            :label="$t('exchange_balances.select_exchange')"
            class="exchange-balances__content__select"
            @change="openExchangeDetails"
          >
            <template #selection="{ item }">
              <div class="exchange-balances__select__image ml-2 mr-6">
                <v-img
                  contain
                  height="42"
                  width="42"
                  :title="exchange"
                  :src="require(`@/assets/images/${item}.png`)"
                  class="exchange-balances__select__icon"
                />
              </div>
              <div
                class="exchange-balances__select__item d-flex flex-column my-3"
              >
                <span class="exchange-balances__select__item__title text-h6">
                  {{ item.charAt(0).toUpperCase() + item.slice(1) }}
                </span>
                <span
                  class="exchange-balances__select__item__amount secondary--text text--lighten-5"
                >
                  <amount-display
                    show-currency="symbol"
                    fiat-currency="USD"
                    :value="exchangeBalance(item)"
                  />
                </span>
              </div>
            </template>
            <template #item="{ item }">
              <div class="exchange-balances__select__image ml-2 mr-6">
                <v-img
                  contain
                  height="42"
                  width="42"
                  :title="exchange"
                  :src="require(`@/assets/images/${item}.png`)"
                  class="exchange-balances__select__icon"
                />
              </div>
              <div
                class="exchange-balances__select__item d-flex flex-column my-3"
              >
                <span class="exchange-balances__select__item__title text-h6">
                  {{ item.charAt(0).toUpperCase() + item.slice(1) }}
                </span>
                <span
                  class="exchange-balances__select__item__amount secondary--text text--lighten-5"
                >
                  <amount-display
                    show-currency="symbol"
                    fiat-currency="USD"
                    :value="exchangeBalance(item)"
                  />
                </span>
              </div>
            </template>
          </v-select>
        </v-col>
        <v-col cols="2" class="hidden-sm-and-down">
          <v-tabs
            fixed-tabs
            vertical
            hide-slider
            optional
            class="exchange-balances__tabs"
          >
            <v-tab
              v-for="(exchange, i) in connectedExchanges"
              :key="i"
              class="exchange-balances__tab ml-3 my-3 py-3"
              active-class="exchange-balances__tab--active"
              :to="`/accounts-balances/exchange-balances/${exchange}`"
              @click="selectedExchange = exchange"
            >
              <v-img
                contain
                height="48"
                width="48"
                :title="exchange"
                :src="require(`@/assets/images/${exchange}.png`)"
                class="exchange-balances__tab__icon"
              />
              <div class="exchange-balances__tab__title d-block mt-2">
                {{ exchange }}
              </div>
              <div class="exchange-balances__tab__amount d-block">
                <amount-display
                  show-currency="symbol"
                  fiat-currency="USD"
                  :value="exchangeBalance(exchange)"
                />
              </div>
            </v-tab>
          </v-tabs>
        </v-col>
        <v-col>
          <asset-balances
            v-if="exchange"
            :balances="exchangeBalances(exchange)"
          />
          <div
            v-else
            class="pa-4"
            v-text="$t('exchange_balances.select_hint')"
          />
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col>
          <i18n path="exchange_balances.no_connected_exchanges">
            <router-link
              to="/settings/api-keys/exchanges"
              v-text="$t('exchange_balances.click_here')"
            />
          </i18n>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapState, mapGetters } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import { AssetBalance } from '@/store/balances/types';
import { ExchangeInfo } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: {
    AssetBalances,
    AmountDisplay
  },
  computed: {
    ...mapState('balances', ['connectedExchanges']),
    ...mapGetters('balances', ['exchangeBalances', 'exchanges'])
  }
})
export default class ExchangeBalances extends Vue {
  @Prop({ required: false, default: '' })
  exchange!: string;
  selectedExchange: string = '';

  connectedExchanges!: string[];
  exchanges!: ExchangeInfo[];
  exchangeBalances!: (exchange: string) => AssetBalance[];

  mounted() {
    this.selectedExchange = this.$route.params.exchange;
  }

  @Watch('$route')
  onRouteChange() {
    // this is necessary to keep the "pre-selected exchange" in sync during the use of history
    // backward/forward events when staying within the same "route" (since the mounted() event doesn't fire)
    this.selectedExchange = this.$route.params.exchange;
  }

  exchangeBalance(exchange: string): BigNumber {
    return this.exchangeBalances(exchange).reduce(
      (sum, asset: AssetBalance) => sum.plus(asset.usdValue),
      Zero
    );
  }

  openExchangeDetails() {
    this.$router.push({
      path: `/accounts-balances/exchange-balances/${this.selectedExchange}`
    });
  }
}
</script>

<style scoped lang="scss">
::v-deep {
  .v-tabs-bar {
    &__content {
      background-color: var(--v-rotki-light-grey-darken1);
      border-radius: 8px 0 0 8px;
      height: 100%;
    }
  }

  .v-tab {
    &__active {
      &::before {
        opacity: 1 !important;
      }
    }
  }
}

.exchange-balances {
  &__content {
    border: 1px solid var(--v-rotki-light-grey-darken2);
    border-radius: 8px;

    &__select {
      border-radius: 8px 8px 0 0;
    }
  }

  &__tabs {
    border-radius: 8px 0 0 8px;
    height: 100%;
  }

  &__tab {
    display: flex;
    flex-direction: column;
    min-height: 125px !important;
    max-height: 125px !important;
    padding-top: 15px;
    padding-bottom: 15px;
    filter: grayscale(100%);
    color: var(--v-rotki-grey-base);
    background-color: transparent;

    &:hover {
      filter: grayscale(0);
      background-color: var(--v-rotki-light-grey-base);
      border-radius: 8px 0 0 8px;
    }

    &:focus {
      filter: grayscale(0);
      border-radius: 8px 0 0 8px;
    }

    &--active {
      filter: grayscale(0);
      border-radius: 8px 0 0 8px;
      background-color: white;
      color: var(--v-secondary-base);

      &:hover {
        border-radius: 8px 0 0 8px;
        background-color: white;
        opacity: 1 !important;
      }

      &:focus {
        border-radius: 8px 0 0 8px;
        opacity: 1 !important;
      }
    }
  }
}
</style>
