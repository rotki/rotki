<script setup lang="ts">
import { TaskType } from '@/types/task-type';
import { Routes } from '@/router/routes';
import { Module } from '@/types/modules';

const { t } = useI18n();
const { isTaskRunning } = useTaskStore();

const { balances, liabilities } = useAggregatedBalances();
const { blockchainTotals } = useAccountBalances();
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

const isBlockchainLoading = computed<boolean>(
  () => get(isQueryingBlockchain) || get(isLoopringLoading)
);

const isExchangeLoading = isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);

const isAllBalancesLoading = isTaskRunning(TaskType.QUERY_BALANCES);

const isManualBalancesLoading = isTaskRunning(TaskType.MANUAL_BALANCES);

const isAnyLoading = logicOr(
  isBlockchainLoading,
  isExchangeLoading,
  isAllBalancesLoading
);

const { refreshBalance } = useRefresh();

const { isModuleEnabled } = useModules();
const nftEnabled = isModuleEnabled(Module.NFTS);

const { dashboardMessage } = useDynamicMessages();
const dismissedMessage = useSessionStorage(
  'rotki.messages.dash.dismissed',
  false
);
</script>

<template>
  <div class="pb-6" data-cy="dashboard">
    <DynamicMessageDisplay
      v-if="dashboardMessage && !dismissedMessage"
      class="!-mt-4"
      :message="dashboardMessage"
      @dismiss="dismissedMessage = true"
    />
    <div class="container">
      <div class="flex flex-wrap gap-6">
        <div class="w-full">
          <OverallBalances />
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 w-full">
          <div class="w-full">
            <SummaryCard
              :name="t('dashboard.exchange_balances.title')"
              can-refresh
              :is-loading="isExchangeLoading"
              :navigates-to="Routes.ACCOUNTS_BALANCES_EXCHANGE"
              @refresh="refreshBalance($event)"
            >
              <SummaryCardCreateButton
                v-if="exchanges.length === 0"
                :to="`#${Routes.API_KEYS_EXCHANGES}?add=true`"
              >
                {{ t('dashboard.exchange_balances.add') }}
              </SummaryCardCreateButton>
              <div v-else data-cy="exchange-balances">
                <ExchangeBox
                  v-for="exchange in exchanges"
                  :key="exchange.location"
                  :location="exchange.location"
                  :amount="exchange.total"
                />
              </div>
            </SummaryCard>
          </div>
          <div class="w-full">
            <SummaryCard
              :name="t('dashboard.blockchain_balances.title')"
              :is-loading="isBlockchainLoading || isTokenDetecting"
              can-refresh
              :navigates-to="Routes.ACCOUNTS_BALANCES"
              @refresh="refreshBalance($event)"
            >
              <template #refreshMenu>
                <BlockchainBalanceRefreshBehaviourMenu />
              </template>
              <SummaryCardCreateButton
                v-if="blockchainTotals.length === 0"
                :to="`#${Routes.ACCOUNTS_BALANCES}?add=true`"
              >
                {{ t('dashboard.blockchain_balances.add') }}
              </SummaryCardCreateButton>
              <div v-else data-cy="blockchain-balances">
                <BlockchainBalanceCardList
                  v-for="total in blockchainTotals"
                  :key="total.chain"
                  :total="total"
                />
              </div>
            </SummaryCard>
          </div>
          <div class="w-full">
            <SummaryCard
              :name="t('dashboard.manual_balances.title')"
              :tooltip="t('dashboard.manual_balances.card_tooltip')"
              :is-loading="isManualBalancesLoading"
              can-refresh
              :navigates-to="Routes.ACCOUNTS_BALANCES_MANUAL"
              @refresh="fetchManualBalances()"
            >
              <SummaryCardCreateButton
                v-if="manualBalanceByLocation.length === 0"
                :to="`#${Routes.ACCOUNTS_BALANCES_MANUAL}?add=true`"
              >
                {{ t('dashboard.manual_balances.add') }}
              </SummaryCardCreateButton>
              <div v-else data-cy="manual-balances">
                <ManualBalanceCardList
                  v-for="manualBalance in manualBalanceByLocation"
                  :key="manualBalance.location"
                  :name="manualBalance.location"
                  :amount="manualBalance.usdValue"
                />
              </div>
            </SummaryCard>
          </div>
        </div>
      </div>
      <div class="flex justify-end my-4">
        <PriceRefresh />
      </div>
      <DashboardAssetTable
        :title="t('common.assets')"
        table-type="ASSETS"
        :loading="isAnyLoading"
        :balances="aggregatedBalances"
      />
      <LiquidityProviderBalanceTable class="mt-8" />
      <DashboardAssetTable
        v-if="aggregatedLiabilities.length > 0"
        class="mt-8"
        table-type="LIABILITIES"
        :title="t('dashboard.liabilities.title')"
        :loading="isAnyLoading"
        :balances="aggregatedLiabilities"
      />
      <NftBalanceTable
        v-if="nftEnabled"
        id="nft-balance-table-section"
        data-cy="nft-balance-table"
        class="mt-8"
      />
    </div>
  </div>
</template>
