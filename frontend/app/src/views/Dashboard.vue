<template>
  <v-container>
    <base-page-header :text="$t('dashboard.title')" />
    <v-row>
      <v-col cols="12">
        <overall-balances />
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
          :is-loading="manualBalancesLoading"
          can-refresh
          @refresh="fetchManualBalances"
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
        <dashboard-asset-table
          :title="$t('dashboard.per_asset_balances.title')"
          :loading="anyIsLoading"
          :balances="aggregatedBalances"
        />
      </v-col>
    </v-row>
    <v-row v-if="liabilities.length > 0">
      <v-col>
        <dashboard-asset-table
          :title="$t('dashboard.liabilities.title')"
          :loading="anyIsLoading"
          :balances="liabilities"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import BlockchainBalanceCardList from '@/components/dashboard/BlockchainBalanceCardList.vue';
import DashboardAssetTable from '@/components/dashboard/DashboardAssetTable.vue';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';
import ManualBalanceCardList from '@/components/dashboard/ManualBalanceCardList.vue';
import OverallBalances from '@/components/dashboard/OverallBalances.vue';
import SummaryCard from '@/components/dashboard/SummaryCard.vue';
import { TaskType } from '@/model/task-type';
import {
  AssetBalance,
  BlockchainBalancePayload,
  BlockchainTotal,
  ExchangeBalancePayload,
  LocationBalance
} from '@/store/balances/types';
import { Blockchain, BTC, ETH, ExchangeInfo, KSM } from '@/typing/types';

@Component({
  components: {
    DashboardAssetTable,
    BasePageHeader,
    OverallBalances,
    SummaryCard,
    ExchangeBox,
    ManualBalanceCardList,
    BlockchainBalanceCardList
  },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('balances', [
      'exchanges',
      'manualBalanceByLocation',
      'aggregatedBalances',
      'liabilities',
      'blockchainTotals',
      'blockchainTotal'
    ])
  },
  methods: {
    ...mapActions('balances', [
      'fetchExchangeBalances',
      'fetchBlockchainBalances',
      'fetchManualBalances'
    ])
  }
})
export default class Dashboard extends Vue {
  exchanges!: ExchangeInfo[];
  isTaskRunning!: (type: TaskType) => boolean;
  blockchainTotals!: BlockchainTotal[];
  aggregatedBalances!: AssetBalance[];
  liabilities!: AssetBalance[];
  manualBalanceByLocation!: LocationBalance[];
  fetchBlockchainBalances!: (
    payload: BlockchainBalancePayload
  ) => Promise<void>;
  fetchExchangeBalances!: (payload: ExchangeBalancePayload) => Promise<void>;
  fetchManualBalances!: () => Promise<void>;

  name(chain: Blockchain): string {
    if (chain === ETH) {
      return this.$t('blockchains.eth').toString();
    } else if (chain === BTC) {
      return this.$t('blockchains.btc').toString();
    } else if (chain === KSM) {
      return this.$t('blockchains.ksm').toString();
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

  get manualBalancesLoading(): boolean {
    return this.isTaskRunning(TaskType.MANUAL_BALANCES);
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
}
</script>
