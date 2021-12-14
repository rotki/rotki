<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <overall-balances />
      </v-col>
    </v-row>
    <v-row justify="center">
      <v-col cols="12" md="4" lg="4">
        <summary-card
          :name="$t('dashboard.exchange_balances.title')"
          can-refresh
          :is-loading="exchangeIsLoading"
          navigates-to="/accounts-balances/exchange-balances/"
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
              :key="exchange.location"
              :location="exchange.location"
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
          navigates-to="/accounts-balances/"
          @refresh="refreshBalance($event)"
        >
          <div slot="tooltip">
            {{ $t('dashboard.blockchain_balances.tooltip') }}
          </div>
          <div v-if="blockchainTotals.length === 0">
            <v-card-actions>
              <v-btn text color="primary" to="/accounts-balances/?add=true">
                {{ $t('dashboard.blockchain_balances.add') }}
              </v-btn>
            </v-card-actions>
          </div>
          <div v-else>
            <blockchain-balance-card-list
              v-for="total in blockchainTotals"
              :key="total.chain"
              :total="total"
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
          navigates-to="/accounts-balances/manual-balances/"
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
                to="/accounts-balances/manual-balances/?add=true"
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
    <v-row justify="end" class="ma-4">
      <v-col cols="auto">
        <price-refresh />
      </v-col>
    </v-row>
    <dashboard-asset-table
      :title="$t('dashboard.per_asset_balances.title')"
      table-type="ASSETS"
      :loading="anyIsLoading"
      :balances="aggregatedBalances"
    />
    <dashboard-asset-table
      v-if="liabilities.length > 0"
      class="mt-8"
      table-type="LIABILITIES"
      :title="$t('dashboard.liabilities.title')"
      :loading="anyIsLoading"
      :balances="liabilities"
    />
    <nft-balance-table data-cy="nft-balance-table" class="mt-8" />
  </v-container>
</template>

<script lang="ts">
import { AssetBalance } from '@rotki/common';
import { Ref } from '@vue/composition-api';
import { mapState } from 'pinia';
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import BlockchainBalanceCardList from '@/components/dashboard/BlockchainBalanceCardList.vue';
import DashboardAssetTable from '@/components/dashboard/DashboardAssetTable.vue';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';
import ManualBalanceCardList from '@/components/dashboard/ManualBalanceCardList.vue';
import NftBalanceTable from '@/components/dashboard/NftBalanceTable.vue';
import OverallBalances from '@/components/dashboard/OverallBalances.vue';
import SummaryCard from '@/components/dashboard/SummaryCard.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import {
  BlockchainBalancePayload,
  BlockchainTotal,
  ExchangeBalancePayload,
  LocationBalance
} from '@/store/balances/types';
import { useTasks } from '@/store/tasks';
import { ExchangeInfo } from '@/types/exchanges';
import { TaskType } from '@/types/task-type';

@Component({
  components: {
    NftBalanceTable,
    PriceRefresh,
    DashboardAssetTable,
    OverallBalances,
    SummaryCard,
    ExchangeBox,
    ManualBalanceCardList,
    BlockchainBalanceCardList
  },
  computed: {
    ...mapState(useTasks, ['isTaskRunning']),
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
      'fetchManualBalances',
      'fetchLoopringBalances'
    ])
  }
})
export default class Dashboard extends Vue {
  exchanges!: ExchangeInfo[];
  isTaskRunning!: (type: TaskType) => Ref<boolean>;
  blockchainTotals!: BlockchainTotal[];
  aggregatedBalances!: AssetBalance[];
  liabilities!: AssetBalance[];
  manualBalanceByLocation!: LocationBalance[];
  fetchBlockchainBalances!: (
    payload: BlockchainBalancePayload
  ) => Promise<void>;
  fetchLoopringBalances!: (refresh: boolean) => Promise<void>;
  fetchExchangeBalances!: (payload: ExchangeBalancePayload) => Promise<void>;
  fetchManualBalances!: () => Promise<void>;

  get blockchainIsLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES).value;
  }

  get exchangeIsLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES).value;
  }

  get allBalancesIsLoading(): boolean {
    return this.isTaskRunning(TaskType.QUERY_BALANCES).value;
  }

  get manualBalancesLoading(): boolean {
    return this.isTaskRunning(TaskType.MANUAL_BALANCES).value;
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
      this.fetchLoopringBalances(true);
    } else if (balanceSource === 'exchange') {
      for (const exchange of this.exchanges) {
        this.fetchExchangeBalances({
          location: exchange.location,
          ignoreCache: true
        });
      }
    }
  }
}
</script>
