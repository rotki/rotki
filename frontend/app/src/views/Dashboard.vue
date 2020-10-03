<template>
  <v-container>
    <base-page-header text="Dashboard" />
    <v-row>
      <v-col cols="12">
        <overall-balances :is-loading="anyIsLoading" />
      </v-col>
    </v-row>
    <v-row class="mr--1" justify="center">
      <v-col cols="12" md="4" lg="4">
        <summary-card
          name="exchange"
          can-refresh
          :is-loading="exchangeIsLoading"
          @refresh="refreshBalance($event)"
        >
          <div slot="tooltip">
            Aggregate value of all balances in each configured exchange.
          </div>
          <div v-if="exchanges.length < 1">
            <v-card-actions>
              <v-btn text color="primary" to="/settings/api-keys/exchanges">
                Add an exchange
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
          name="blockchain"
          :is-loading="blockchainIsLoading"
          can-refresh
          @refresh="refreshBalance($event)"
        >
          <div slot="tooltip">
            Aggregate value of all configured addresses in each blockchain.
          </div>
          <div
            v-if="
              blockchainTotals.ethereum === zero &&
              blockchainTotals.bitcoin === zero
            "
          >
            <v-card-actions>
              <v-btn text color="primary" to="/accounts-balances">
                Add blockchain address
              </v-btn>
            </v-card-actions>
          </div>
          <div v-else>
            <blockchain-balance-card-list
              v-for="(usdValue, protocol) in blockchainTotals"
              :key="protocol"
              :name="protocol"
              :amount="usdValue"
            />
          </div>
        </summary-card>
      </v-col>
      <v-col cols="12" md="4" lg="4">
        <summary-card
          name="manual"
          tooltip="Aggregate value of manual balances entered. Fiat balances are aggregated in the banks entry."
        >
          <div slot="tooltip">
            Aggregate value of manual balances entered
          </div>
          <div v-if="Object.keys(manualBalanceByLocation).length < 1">
            <v-card-actions>
              <v-btn
                text
                color="primary"
                to="/accounts-balances/manual-balances"
              >
                Add a manual balance
              </v-btn>
            </v-card-actions>
          </div>
          <div v-else>
            <manual-balance-card-list
              v-for="(usdValue, location) in manualBalanceByLocation"
              :key="location"
              :name="location"
              :amount="usdValue"
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
              balance per asset
            </v-toolbar-title>
            <v-spacer />
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              label="Search"
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
              {{ currency.ticker_symbol }} value
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
              <percentage-display
                :value="item.usdValue | percentage(total, floatingPrecision)"
              />
            </template>
            <template #no-results>
              <span class="grey--text text--darken-2">
                Your search for "{{ search }}" yielded no results.
              </span>
            </template>
            <template
              v-if="aggregatedBalances.length > 0 && search.length < 1"
              #body.append
            >
              <tr class="dashboard__balances__total font-weight-medium">
                <td>Total</td>
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
import { createNamespacedHelpers } from 'vuex';
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
  AccountWithBalance,
  AssetBalance,
  BlockchainBalancePayload,
  ExchangeBalancePayload,
  ManualBalanceByLocation
} from '@/store/balances/types';
import { ExchangeInfo } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances');
const { mapGetters } = createNamespacedHelpers('session');

interface BlockchainBalances {
  [protocol: string]: BigNumber;
}

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
    ...mapTaskGetters(['isTaskRunning']),
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalanceGetters([
      'exchanges',
      'manualBalanceByLocation',
      'exchangeRate',
      'aggregatedBalances',
      'ethAccounts',
      'btcAccounts',
      'blockchainTotal'
    ])
  }
})
export default class Dashboard extends Vue {
  currency!: Currency;
  floatingPrecision!: number;
  exchanges!: ExchangeInfo;
  blockchainTotal!: BigNumber;
  ethAccounts!: AccountWithBalance[];
  btcAccounts!: AccountWithBalance[];
  isTaskRunning!: (type: TaskType) => boolean;

  aggregatedBalances!: AssetBalance[];
  manualBalanceByLocation!: ManualBalanceByLocation;

  zero: BigNumber = Zero;

  footerProps = footerProps;

  get blockchainTotals(): BlockchainBalances {
    const ethereumTotal = this.ethAccounts.reduce(
      (sum: BigNumber, { balance }: AccountWithBalance) => {
        return sum.plus(balance.usdValue);
      },
      Zero
    );

    const bitcoinTotal = this.btcAccounts.reduce(
      (sum: BigNumber, { balance }: AccountWithBalance) => {
        return sum.plus(balance.usdValue);
      },
      Zero
    );

    return { ethereum: ethereumTotal, bitcoin: bitcoinTotal };
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
    switch (balanceSource) {
      case 'blockchain':
        this.$store.dispatch('balances/fetchBlockchainBalances', {
          ignoreCache: true
        } as BlockchainBalancePayload);
        break;
      case 'exchange':
        Object.values(this.exchanges).forEach(exchange => {
          this.$store.dispatch('balances/fetchExchangeBalances', {
            name: exchange.name,
            ignoreCache: true
          } as ExchangeBalancePayload);
        });
        break;
      default:
        break;
    }
  }

  get total(): BigNumber {
    return this.aggregatedBalances.reduce(
      (sum, asset) => sum.plus(asset.usdValue),
      Zero
    );
  }
  search: string = '';

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'Value', value: 'usdValue', align: 'end' },
    {
      text: '% of net Value',
      value: 'percentage',
      align: 'end',
      sortable: false
    }
  ];
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
