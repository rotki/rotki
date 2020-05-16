<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <overall-balances
          :is-loading="blockchainIsLoading || exchangeIsLoading"
        ></overall-balances>
      </v-col>
    </v-row>
    <v-row class="mx-0 flex" justify="center">
      <v-col cols="12" md="4" lg="4">
        <summary-card
          name="exchange"
          can-refresh
          :is-loading="exchangeIsLoading"
          @refresh="refreshBalance($event)"
        >
          <div slot="tooltip">
            Aggregate value of all balances<br />in each configured exchange.
          </div>
          <div v-if="exchanges.length < 1">
            <v-card-actions>
              <v-btn text color="primary" to="/settings/api-keys">
                Add an exchange
              </v-btn>
            </v-card-actions>
          </div>
          <div v-else>
            <exchange-box
              v-for="exchange in exchanges"
              :key="exchange.name + '_new'"
              :name="exchange.name"
              :amount="exchange.total"
            ></exchange-box>
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
            Aggregate value of all configured<br />addresses in each blockchain.
          </div>
          <div
            v-if="
              blockchainTotals.ethereum === zero &&
              blockchainTotals.bitcoin === zero
            "
          >
            <v-card-actions>
              <v-btn text color="primary" to="/blockchain-accounts">
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
            ></blockchain-balance-card-list>
          </div>
        </summary-card>
      </v-col>
      <v-col cols="12" md="4" lg="4">
        <summary-card
          name="manual"
          tooltip="Aggregate value of manual balances entered. Fiat balances are aggregated in the banks entry."
        >
          <div slot="tooltip">
            Aggregate value of manual balances entered.<br />Fiat balances are
            aggregated in the banks entry.
          </div>
          <div v-if="Object.keys(manualBalanceByLocation).length < 1">
            <v-card-actions>
              <v-btn text color="primary" to="/blockchain-accounts">
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
            ></manual-balance-card-list>
          </div>
        </summary-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-row no-gutters class="pa-3 rotkibeige primary--text">
            <v-toolbar-title class="font-weight-medium">
              balance per asset
            </v-toolbar-title>
            <v-spacer></v-spacer>
            <v-text-field
              v-model="search"
              append-icon="fa-search"
              label="Search"
              class="pa-0 ma-0"
              single-line
              hide-details
            ></v-text-field>
          </v-row>
          <v-data-table
            class="dashboard__balances"
            :headers="headers"
            :items="aggregatedBalances"
            :search="search"
            :loading="blockchainIsLoading || exchangeIsLoading"
            sort-by="usdValue"
            sort-desc
          >
            <template #header.usdValue>
              {{ currency.ticker_symbol }} value
            </template>
            <template #item.asset="{ item }">
              <asset-details :asset="item.asset"></asset-details>
            </template>
            <template #item.amount="{ item }">
              <amount-display :value="item.amount"></amount-display>
            </template>
            <template #item.usdValue="{ item }">
              <amount-display
                :fiat-currency="item.asset"
                :amount="item.amount"
                :value="item.usdValue"
              ></amount-display>
            </template>
            <template #item.percentage="{ item }">
              <amount-display
                :value="item.usdValue | percentage(total, floatingPrecision)"
              ></amount-display>
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
              <tr class="dashboard__balances__total">
                <td>Total</td>
                <td></td>
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
                  ></amount-display>
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
import CryptoIcon from '@/components/CryptoIcon.vue';
import BlockchainBalanceCardList from '@/components/dashboard/BlockchainBalanceCardList.vue';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';
import InformationBox from '@/components/dashboard/InformationBox.vue';
import ManualBalanceCardList from '@/components/dashboard/ManualBalanceCardList.vue';
import OverallBalances from '@/components/dashboard/OverallBalances.vue';
import SummaryCard from '@/components/dashboard/SummaryCard.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';

import {
  AssetBalance,
  ManualBalanceByLocation,
  AccountBalance
} from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';
import { TaskType } from '@/model/task';
import {
  BlockchainBalancePayload,
  ExchangeBalancePayload
} from '@/store/balances/actions';
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
    AmountDisplay,
    OverallBalances,
    AssetDetails,
    SummaryCard,
    ExchangeBox,
    InformationBox,
    ManualBalanceCardList,
    BlockchainBalanceCardList,
    CryptoIcon
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
  ethAccounts!: AccountBalance[];
  btcAccounts!: AccountBalance[];
  isTaskRunning!: (type: TaskType) => boolean;

  aggregatedBalances!: AssetBalance[];
  manualBalanceByLocation!: ManualBalanceByLocation;

  zero: BigNumber = Zero;

  get blockchainTotals(): BlockchainBalances {
    const ethereumTotal = this.ethAccounts.reduce(
      (sum: BigNumber, account: AccountBalance) => {
        return sum.plus(account.usdValue);
      },
      Zero
    );

    const bitcoinTotal = this.btcAccounts.reduce(
      (sum: BigNumber, account: AccountBalance) => {
        return sum.plus(account.usdValue);
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

<style scoped lang="scss"></style>
