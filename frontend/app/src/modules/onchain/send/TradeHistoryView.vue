<script setup lang="ts">
import type { RecentTransaction } from '@/modules/onchain/types';
import TradeHistoryItem from '@/modules/onchain/send/TradeHistoryItem.vue';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';

const openDialog = ref<boolean>(false);
const tabValue = ref(0);

const { t } = useI18n();

const { recentTransactions } = storeToRefs(useWalletStore());

const pendingTransactions = computed<RecentTransaction[]>(() =>
  get(recentTransactions).filter(tx => tx.status === 'pending'),
);

const completedTransactions = computed<RecentTransaction[]>(() =>
  get(recentTransactions).filter(tx => tx.status === 'completed'),
);

const failedTransactions = computed<RecentTransaction[]>(() =>
  get(recentTransactions).filter(tx => tx.status === 'failed'),
);

const tabs = computed<{ label: string; transactions: RecentTransaction[] }[]>(() => [
  { label: t('trade_history_view.labels.all'), transactions: get(recentTransactions) },
  { label: t('trade_history_view.labels.completed'), transactions: get(completedTransactions) },
  { label: t('trade_history_view.labels.pending'), transactions: get(pendingTransactions) },
  { label: t('trade_history_view.labels.failed'), transactions: get(failedTransactions) },
]);
</script>

<template>
  <div>
    <RuiButton
      variant="outlined"
      color="primary"
      size="sm"
      class="h-full"
      @click="openDialog = true"
    >
      <div
        v-if="pendingTransactions.length > 0"
        class="flex items-center"
      >
        <RuiProgress
          circular
          variant="indeterminate"
          color="primary"
          class="flex"
          thickness="2"
          size="16"
        />
      </div>

      <RuiIcon
        v-else
        name="lu-history"
        size="18"
      />
    </RuiButton>

    <RuiDialog
      v-model="openDialog"
      max-width="500"
    >
      <RuiCard
        divide
        no-padding
        content-class="overflow-hidden"
      >
        <template #header>
          {{ t('trade.recent_transactions.title') }}
        </template>
        <div class="max-h-[calc(100vh-400px)] overflow-auto ">
          <RuiTabs
            v-model="tabValue"
            color="primary"
          >
            <RuiTab
              v-for="tab in tabs"
              :key="tab.label"
            >
              {{ tab.label }}
            </RuiTab>
          </RuiTabs>
          <RuiTabItems v-model="tabValue">
            <RuiTabItem
              v-for="tab in tabs"
              :key="tab.label"
            >
              <div
                v-if="tab.transactions.length > 0"
              >
                <TradeHistoryItem
                  v-for="item in tab.transactions"
                  :key="item.hash"
                  :item="item"
                />
              </div>
              <div
                v-else
                class="text-rui-text-secondary p-4"
              >
                {{ t('trade.recent_transactions.no_data') }}
              </div>
            </RuiTabItem>
          </RuiTabItems>
        </div>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
