<template>
  <v-container>
    <card class="exchange-balances mt-8" outlined-body>
      <template #title>
        {{ $t('exchange_balances.title') }}
      </template>
      <v-btn
        absolute
        fab
        top
        right
        dark
        color="primary"
        to="/settings/api-keys/exchanges"
      >
        <v-icon> mdi-plus </v-icon>
      </v-btn>
      <v-row
        v-if="usedExchanges.length > 0"
        no-gutters
        class="exchange-balances__content"
      >
        <v-col cols="12" class="hidden-md-and-up">
          <v-select
            v-model="selectedExchange"
            filled
            :items="usedExchanges"
            hide-details
            :label="$t('exchange_balances.select_exchange')"
            class="exchange-balances__content__select"
            @change="openExchangeDetails"
          >
            <template #selection="{ item }">
              <exchange-amount-row
                :balance="exchangeBalance(item)"
                :exchange="exchange"
              />
            </template>
            <template #item="{ item }">
              <exchange-amount-row
                :balance="exchangeBalance(item)"
                :exchange="exchange"
              />
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
              v-for="(exchange, i) in usedExchanges"
              :key="i"
              class="exchange-balances__tab ml-3 my-3 py-3 text-none"
              active-class="exchange-balances__tab--active"
              :to="`/accounts-balances/exchange-balances/${exchange}`"
              @click="selectedExchange = exchange"
            >
              <location-display :identifier="exchange" size="36px" />
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
        <v-col
          :class="
            $vuetify.breakpoint.mdAndUp ? 'exchange-balances__balances' : null
          "
        >
          <asset-balances
            v-if="exchange"
            flat
            :balances="exchangeBalances(exchange)"
          />
          <div v-else class="pa-4">
            {{ $t('exchange_balances.select_hint') }}
          </div>
        </v-col>
      </v-row>
      <v-row v-else class="px-4 py-8">
        <v-col>
          <i18n path="exchange_balances.no_connected_exchanges">
            <router-link to="/settings/api-keys/exchanges">
              {{ $t('exchange_balances.click_here') }}
            </router-link>
          </i18n>
        </v-col>
      </v-row>
    </card>
  </v-container>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapState, mapGetters } from 'vuex';
import ExchangeAmountRow from '@/components/accounts/exchanges/ExchangeAmountRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { tradeLocations } from '@/components/history/consts';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import { Exchange } from '@/model/action-result';
import { AssetBalance } from '@/store/balances/types';
import { ExchangeInfo } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';

@Component({
  components: {
    ExchangeAmountRow,
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

  connectedExchanges!: Exchange[];
  exchanges!: ExchangeInfo[];
  exchangeBalances!: (exchange: string) => AssetBalance[];

  get usedExchanges(): string[] {
    return this.connectedExchanges
      .map(({ location }) => location)
      .filter(uniqueStrings);
  }

  mounted() {
    this.selectedExchange = this.$route.params.exchange;
  }

  getIcon(exchange: string): string {
    const location = tradeLocations.find(
      ({ identifier }) => identifier === exchange
    );
    return location?.icon ?? '';
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
      border-radius: 4px 0 0 4px;
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
    &__select {
      border-radius: 4px 4px 0 0;

      ::v-deep {
        .v-input {
          &__icon {
            &--append {
              margin-top: 24px;
            }
          }
        }
      }
    }
  }

  &__balances {
    border-left: var(--v-rotki-light-grey-darken1) solid thin;
  }

  &__tabs {
    border-radius: 4px 0 0 4px;
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
      border-radius: 4px 0 0 4px;
    }

    &:focus {
      filter: grayscale(0);
      border-radius: 4px 0 0 4px;
    }

    &--active {
      filter: grayscale(0);
      border-radius: 4px 0 0 4px;
      background-color: white;
      color: var(--v-secondary-base);

      &:hover {
        border-radius: 4px 0 0 4px;
        background-color: white;
        opacity: 1 !important;
      }

      &:focus {
        border-radius: 4px 0 0 4px;
        opacity: 1 !important;
      }
    }

    /* stylelint-disable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
    .theme--dark &--active {
      background-color: var(--v-dark-lighten1);
      color: white;

      &:hover {
        background-color: var(--v-dark-base) !important;
      }
    }
    /* stylelint-enable selector-class-pattern,selector-nested-pattern, rule-empty-line-before */
  }
}
</style>
