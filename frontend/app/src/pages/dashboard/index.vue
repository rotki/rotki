<script setup lang="ts">
import { TaskType } from '@/types/task-type';
import { Routes } from '@/router/routes';
import { Module } from '@/types/modules';

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
  () => import('@/components/dashboard/summary-card/SummaryCard.vue')
);
const BlockchainBalanceRefreshBehaviourMenu = defineAsyncComponent(
  () =>
    import('@/components/dashboard/BlockchainBalanceRefreshBehaviourMenu.vue')
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
const { isTaskRunning } = useTaskStore();

const { balances, liabilities } = useAggregatedBalancesStore();
const { blockchainTotals } = storeToRefs(useAccountBalancesStore());
const aggregatedBalances = balances();
const aggregatedLiabilities = liabilities();

const manualBalancesStore = useManualBalancesStore();
const { fetchManualBalances } = manualBalancesStore;
const { manualBalanceByLocation } = storeToRefs(manualBalancesStore);

const exchangeStore = useExchangeBalancesStore();
const { exchanges } = storeToRefs(exchangeStore);

const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);
const isTokenDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS);

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

const { refreshBalance } = useRefresh();

const { isModuleEnabled } = useModules();
const nftEnabled = isModuleEnabled(Module.NFTS);
</script>

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
            :navigates-to="Routes.ACCOUNTS_BALANCES_EXCHANGE"
            @refresh="refreshBalance($event)"
          >
            <div v-if="exchanges.length === 0">
              <v-card-actions class="px-4">
                <v-btn
                  text
                  block
                  color="primary"
                  :to="`${Routes.API_KEYS_EXCHANGES}?add=true`"
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
            :is-loading="isBlockchainLoading || isTokenDetecting"
            can-refresh
            :navigates-to="Routes.ACCOUNTS_BALANCES"
            @refresh="refreshBalance($event)"
          >
            <template #refreshMenu>
              <blockchain-balance-refresh-behaviour-menu />
            </template>
            <div v-if="blockchainTotals.length === 0">
              <v-card-actions class="px-4">
                <v-btn
                  text
                  block
                  color="primary"
                  :to="`${Routes.ACCOUNTS_BALANCES}?add=true`"
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
            <div v-else data-cy="blockchain-balances">
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
            :name="tc('dashboard.manual_balances.title')"
            :tooltip="tc('dashboard.manual_balances.card_tooltip')"
            :is-loading="isManualBalancesLoading"
            can-refresh
            :navigates-to="Routes.ACCOUNTS_BALANCES_MANUAL"
            @refresh="fetchManualBalances"
          >
            <div v-if="manualBalanceByLocation.length === 0">
              <v-card-actions class="px-4">
                <v-btn
                  text
                  block
                  color="primary"
                  :to="`${Routes.ACCOUNTS_BALANCES_MANUAL}?add=true`"
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
            <div v-else data-cy="manual-balances">
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
        v-if="aggregatedLiabilities.length > 0"
        class="mt-8"
        table-type="LIABILITIES"
        :title="tc('dashboard.liabilities.title')"
        :loading="isAnyLoading"
        :balances="aggregatedLiabilities"
      />
      <nft-balance-table
        v-if="nftEnabled"
        data-cy="nft-balance-table"
        class="mt-8"
      />
    </v-container>
  </div>
</template>
