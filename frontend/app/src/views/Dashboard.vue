<template>
  <div class="pb-6">
    <v-container>
      <v-row>
        <v-col cols="12">
          <overall-balances />
        </v-col>
        <v-col cols="12" md="4" lg="4">
          <summary-card
            :name="t('dashboard.exchange_balances.title')"
            can-refresh
            :is-loading="isExchangeLoading"
            navigates-to="/accounts-balances/exchange-balances/"
            @refresh="refreshBalance($event)"
          >
            <div slot="tooltip">
              {{ t('dashboard.exchange_balances.tooltip') }}
            </div>
            <div v-if="exchanges.length < 1">
              <v-card-actions class="px-4">
                <v-btn
                  text
                  block
                  color="primary"
                  to="/settings/api-keys/exchanges?add=true"
                  class="py-8"
                >
                  <div class="d-flex flex-column align-center">
                    <v-icon class="mb-2">mdi-plus-circle-outline</v-icon>
                    <span>
                      {{ t('dashboard.exchange_balances.add') }}
                    </span>
                  </div>
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
            :name="tc('dashboard.blockchain_balances.title')"
            :is-loading="isBlockchainLoading"
            can-refresh
            navigates-to="/accounts-balances/"
            @refresh="refreshBalance($event)"
          >
            <div slot="tooltip">
              {{ tc('dashboard.blockchain_balances.tooltip') }}
            </div>
            <div v-if="blockchainSummary.length === 0">
              <v-card-actions class="px-4">
                <v-btn
                  text
                  block
                  color="primary"
                  to="/accounts-balances/?add=true"
                  class="py-8"
                >
                  <div class="d-flex flex-column align-center">
                    <v-icon class="mb-2">mdi-plus-circle-outline</v-icon>
                    <span>
                      {{ tc('dashboard.blockchain_balances.add') }}
                    </span>
                  </div>
                </v-btn>
              </v-card-actions>
            </div>
            <div v-else>
              <blockchain-balance-card-list
                v-for="total in blockchainSummary"
                :key="total.chain"
                :total="total"
              />
            </div>
          </summary-card>
        </v-col>
        <v-col cols="12" md="4" lg="4">
          <summary-card
            :name="tc('dashboard.manual_balances.title')"
            :tooltip="tc('dashboard.manual_balances.card_tooltip')"
            :is-loading="isManualBalancesLoading"
            can-refresh
            navigates-to="/accounts-balances/manual-balances/"
            @refresh="fetchManualBalances"
          >
            <div slot="tooltip">
              {{ t('dashboard.manual_balances.tooltip') }}
            </div>
            <div v-if="manualBalanceByLocation.length < 1">
              <v-card-actions class="px-4">
                <v-btn
                  text
                  block
                  color="primary"
                  to="/accounts-balances/manual-balances/?add=true"
                  class="py-8"
                >
                  <div class="d-flex flex-column align-center">
                    <v-icon class="mb-2">mdi-plus-circle-outline</v-icon>
                    <span>
                      {{ t('dashboard.manual_balances.add') }}
                    </span>
                  </div>
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
      <v-row justify="end" class="my-4">
        <v-col cols="auto">
          <price-refresh />
        </v-col>
      </v-row>
      <dashboard-asset-table
        :title="tc('common.assets')"
        table-type="ASSETS"
        :loading="isAnyLoading"
        :balances="aggregatedBalances"
      />
      <liquidity-provider-balance-table class="mt-8" />
      <dashboard-asset-table
        v-if="liabilities.length > 0"
        class="mt-8"
        table-type="LIABILITIES"
        :title="tc('dashboard.liabilities.title')"
        :loading="isAnyLoading"
        :balances="liabilities"
      />
      <nft-balance-table data-cy="nft-balance-table" class="mt-8" />
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const PriceRefresh = defineAsyncComponent(
  () => import('@/components/helper/PriceRefresh.vue')
);
const DashboardAssetTable = defineAsyncComponent(
  () => import('@/components/dashboard/DashboardAssetTable.vue')
);
const OverallBalances = defineAsyncComponent(
  () => import('@/components/dashboard/OverallBalances.vue')
);
const SummaryCard = defineAsyncComponent(
  () => import('@/components/dashboard/SummaryCard.vue')
);
const ExchangeBox = defineAsyncComponent(
  () => import('@/components/dashboard/ExchangeBox.vue')
);
const ManualBalanceCardList = defineAsyncComponent(
  () => import('@/components/dashboard/ManualBalanceCardList.vue')
);
const BlockchainBalanceCardList = defineAsyncComponent(
  () => import('@/components/dashboard/BlockchainBalanceCardList.vue')
);
const NftBalanceTable = defineAsyncComponent(
  () => import('@/components/dashboard/NftBalanceTable.vue')
);
const LiquidityProviderBalanceTable = defineAsyncComponent(
  () => import('@/components/dashboard/LiquidityProviderBalanceTable.vue')
);

const { t, tc } = useI18n();
const { isTaskRunning } = useTasks();

const blockchainBalancesStore = useBlockchainBalancesStore();

const { aggregatedBalances, liabilities } = storeToRefs(
  blockchainBalancesStore
);
const { fetchBlockchainBalances, fetchLoopringBalances } =
  blockchainBalancesStore;

const { blockchainSummary } = storeToRefs(useBlockchainAccountsStore());

const manualBalancesStore = useManualBalancesStore();
const { fetchManualBalances } = manualBalancesStore;
const { manualBalanceByLocation } = storeToRefs(manualBalancesStore);

const exchangeStore = useExchangeBalancesStore();
const { exchanges } = storeToRefs(exchangeStore);
const { fetchConnectedExchangeBalances } = exchangeStore;

const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);
const isBlockchainLoading = computed<boolean>(() => {
  return get(isQueryingBlockchain) || get(isLoopringLoading);
});

const isExchangeLoading = isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);

const isAllBalancesLoading = isTaskRunning(TaskType.QUERY_BALANCES);

const isManualBalancesLoading = isTaskRunning(TaskType.MANUAL_BALANCES);

const isAnyLoading = computed<boolean>(() => {
  return (
    get(isBlockchainLoading) ||
    get(isExchangeLoading) ||
    get(isAllBalancesLoading)
  );
});

const refreshBalance = (balanceSource: string) => {
  if (balanceSource === 'blockchain') {
    fetchBlockchainBalances({
      ignoreCache: true
    });
    fetchLoopringBalances(true);
  } else if (balanceSource === 'exchange') {
    fetchConnectedExchangeBalances(true);
  }
};
</script>
