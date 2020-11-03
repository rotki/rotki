<template>
  <v-container>
    <base-page-header :text="$t('dashboard.title')" />
    <v-row>
      <v-col cols="12">
        <overall-balances :is-loading="anyIsLoading" />
      </v-col>
    </v-row>
    <v-row class="mr--1" justify="center">
      <v-col cols="12" md="4" lg="4">
        <summary-card
          :name="$t('dashboard.exchange_balances.title')"
          can-refresh
          :is-loading="exchangeIsLoading"
          @refresh="refreshBalance($event)"
        >
          <div slot="tooltip">
            {{ $t('dashboard.exchange_balances.tooltip') }}
          </div>
          <div v-if="exchanges.length < 1">
            <v-card-actions>
              <v-btn text color="primary" to="/settings/api-keys/exchanges">
                {{ $t('dashboard.exchange_balances.add') }}
              </v-btn>
            </v-card-actions>
          </div>
          <div v-else>
            <exchange-box
              v-for="exchange in exchanges"
              :key="exchange.name"
              :name="exchange.name"
              :amount="exchange.total"
            />
          </div>
        </summary-card>
      </v-col>
      <v-col cols="12" md="4" lg="4">
        <summary-card
          :name="$t('dashboard.blockchain_balances.title')"
          :is-loading="blockchainIsLoading"
          can-refresh
          @refresh="refreshBalance($event)"
        >
          <div slot="tooltip">
            {{ $t('dashboard.blockchain_balances.tooltip') }}
          </div>
          <div v-if="blockchainTotals.length === 0">
            <v-card-actions>
              <v-btn text color="primary" to="/accounts-balances">
                {{ $t('dashboard.blockchain_balances.add') }}
              </v-btn>
            </v-card-actions>
          </div>
          <div v-else>
            <blockchain-balance-card-list
              v-for="total in blockchainTotals"
              :key="total.chain"
              :chain="total.chain"
              :name="name(total.chain)"
              :loading="total.loading"
              :amount="total.usdValue"
            />
          </div>
        </summary-card>
      </v-col>
      <v-col cols="12" md="4" lg="4">
        <summary-card
          :name="$t('dashboard.manual_balances.title')"
          :tooltip="$t('dashboard.manual_balances.card_tooltip')"
        >
          <div slot="tooltip">
            {{ $t('dashboard.manual_balances.tooltip') }}
          </div>
          <div v-if="manualBalanceByLocation.length < 1">
            <v-card-actions>
              <v-btn
                text
                color="primary"
                to="/accounts-balances/manual-balances"
              >
                {{ $t('dashboard.manual_balances.add') }}
              </v-btn>
            </v-card-actions>
          </div>
          <div v-else>
            <manual-balance-card-list
              v-for="manualBalance in manualBalanceByLocation"
              :key="manualBalance.location"
              :name="manualBalance.location"
              :amount="manualBalance.usdValue"
            />
          </div>
        </summary-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-row no-gutters class="pa-3 secondary--text">
            <v-toolbar-title class="font-weight-medium">
              {{ $t('dashboard.per_asset_balances.title') }}
            </v-toolbar-title>
            <v-spacer />
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              :label="$t('dashboard.per_asset_balances.search')"
              class="pa-0 ma-0"
              single-line
              hide-details
            />
          </v-row>
          <v-data-table
            class="dashboard__balances"
            :headers="headers"
            :items="aggregatedBalances"
            :search="search"
            :loading="anyIsLoading"
            sort-by="usdValue"
            sort-desc
            :footer-props="footerProps"
          >
            <template #header.usdValue>
              {{
                $t('dashboard.per_asset_balances.headers.value', {
                  symbol: currency.ticker_symbol
                })
              }}
            </template>
            <template #item.asset="{ item }">
              <asset-details :asset="item.asset" />
            </template>
            <template #item.amount="{ item }">
              <amount-display :value="item.amount" />
            </template>
            <template #item.usdValue="{ item }">
              <amount-display
                show-currency="symbol"
                :fiat-currency="item.asset"
                :amount="item.amount"
                :value="item.usdValue"
              />
            </template>
            <template #item.percentage="{ item }">
              <percentage-display :value="percentage(item.usdValue, total)" />
            </template>
            <template #no-results>
              <span class="grey--text text--darken-2">
                {{
                  $t('dashboard.per_asset_balances.no_search_result', {
                    search
                  })
                }}
              </span>
            </template>
            <template
              v-if="aggregatedBalances.length > 0 && search.length < 1"
              #body.append
            >
              <tr class="dashboard__balances__total font-weight-medium">
                <td>{{ $t('dashboard.per_asset_balances.total') }}</td>
                <td />
                <td class="text-end">
                  <amount-display
                    :fiat-currency="currency.ticker_symbol"
                    :value="
                      aggregatedBalances
                        | aggregateTotal(
                          currency.ticker_symbol,
                          exchangeRate(currency.ticker_symbol),
                          floatingPrecision
                        )
                    "
                    show-currency="symbol"
                  />
                </td>
              </tr>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapGetters } from 'vuex';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import BlockchainBalanceCardList from '@/components/dashboard/BlockchainBalanceCardList.vue';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';
import ManualBalanceCardList from '@/components/dashboard/ManualBalanceCardList.vue';
import OverallBalances from '@/components/dashboard/OverallBalances.vue';
import SummaryCard from '@/components/dashboard/SummaryCard.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import { footerProps } from '@/config/datatable.common';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task-type';
import {
  AssetBalance,
  BlockchainBalancePayload,
  BlockchainTotal,
  ExchangeBalancePayload,
  LocationBalance
} from '@/store/balances/types';
import { Blockchain, BTC, ETH, ExchangeInfo } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: {
    PercentageDisplay,
    AmountDisplay,
    BasePageHeader,
    OverallBalances,
    AssetDetails,
    SummaryCard,
    ExchangeBox,
    ManualBalanceCardList,
    BlockchainBalanceCardList
  },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('session', ['floatingPrecision', 'currency']),
    ...mapGetters('balances', [
      'exchanges',
      'manualBalanceByLocation',
      'exchangeRate',
      'aggregatedBalances',
      'blockchainTotals',
      'blockchainTotal'
    ])
  },
  methods: {
    ...mapActions('balances', [
      'fetchExchangeBalances',
      'fetchBlockchainBalances'
    ])
  }
})
export default class Dashboard extends Vue {
  readonly headers: DataTableHeader[] = [
    {
      text: this.$tc('dashboard.per_asset_balances.headers.asset'),
      value: 'asset'
    },
    {
      text: this.$tc('dashboard.per_asset_balances.headers.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$tc('dashboard.per_asset_balances.headers.value'),
      value: 'usdValue',
      align: 'end'
    },
    {
      text: this.$tc('dashboard.per_asset_balances.headers.percentage'),
      value: 'percentage',
      align: 'end',
      sortable: false
    }
  ];

  search: string = '';

  currency!: Currency;
  floatingPrecision!: number;
  exchanges!: ExchangeInfo[];
  isTaskRunning!: (type: TaskType) => boolean;
  blockchainTotals!: BlockchainTotal[];
  aggregatedBalances!: AssetBalance[];
  manualBalanceByLocation!: LocationBalance[];
  footerProps = footerProps;
  fetchBlockchainBalances!: (
    payload: BlockchainBalancePayload
  ) => Promise<void>;
  fetchExchangeBalances!: (payload: ExchangeBalancePayload) => Promise<void>;

  percentage(value: BigNumber, total: BigNumber): string {
    return value.div(total).multipliedBy(100).toFixed(2);
  }

  name(chain: Blockchain): string {
    if (chain === ETH) {
      return this.$tc('blockchains.eth');
    } else if (chain === BTC) {
      return this.$tc('blockchains.btc');
    }
    return '';
  }

  get blockchainIsLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  }

  get exchangeIsLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);
  }

  get allBalancesIsLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BALANCES);
  }

  get anyIsLoading(): boolean {
    return (
      this.blockchainIsLoading ||
      this.exchangeIsLoading ||
      this.allBalancesIsLoading
    );
  }

  refreshBalance(balanceSource: string) {
    if (balanceSource === 'blockchain') {
      this.fetchBlockchainBalances({
        ignoreCache: true
      });
    } else if (balanceSource === 'exchange') {
      for (const exchange of this.exchanges) {
        this.fetchExchangeBalances({
          name: exchange.name,
          ignoreCache: true
        });
      }
    }
  }

  get total(): BigNumber {
    return this.aggregatedBalances.reduce(
      (sum, asset) => sum.plus(asset.usdValue),
      Zero
    );
  }
}
</script>

<style scoped lang="scss">
.dashboard {
  &__balances {
    &__total {
      &:hover {
        background-color: transparent !important;
      }
    }
  }
}
</style>
