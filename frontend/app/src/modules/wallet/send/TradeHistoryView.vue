<script setup lang="ts">
import type { RecentTransaction } from '@/modules/wallet/types';
import TradeHistoryItem from '@/modules/wallet/send/TradeHistoryItem.vue';
import { useWalletStore } from '@/modules/wallet/use-wallet-store';

const openDialog = ref<boolean>(false);
const tabValue = ref(0);

const { t } = useI18n({ useScope: 'global' });

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
    <RuiTooltip :open-delay="200">
      <template #activator>
        <RuiButton
          variant="text"
          icon
          :aria-label="t('trade.recent_transactions.title')"
          data-testid="trade-history-open"
          @click="openDialog = true"
        >
          <RuiProgress
            v-if="pendingTransactions.length > 0"
            circular
            variant="indeterminate"
            color="primary"
            thickness="2"
            size="18"
          />
          <RuiIcon
            v-else
            name="lu-history"
            size="18"
          />
        </RuiButton>
      </template>
      {{ t('trade.recent_transactions.title') }}
    </RuiTooltip>

    <RuiDialog
      v-model="openDialog"
      max-width="500"
    >
      <RuiCard
        divide
        no-padding
        :class-names="{ content: 'overflow-hidden' }"
      >
        <template #header>
          {{ t('trade.recent_transactions.title') }}
        </template>
        <RuiButton
          variant="text"
          class="absolute top-2 right-2"
          icon
          :aria-label="t('common.actions.close')"
          data-testid="trade-history-close"
          @click="openDialog = false"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
        <RuiTabs
          v-model="tabValue"
          color="primary"
          class="border-b border-default"
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
              class="h-[min(24rem,50vh)] overflow-auto between:border-t between:border-default"
            >
              <TradeHistoryItem
                v-for="item in tab.transactions"
                :key="item.hash"
                :item="item"
              />
            </div>
            <div
              v-else
              class="h-[min(24rem,50vh)] flex items-center justify-center text-sm text-rui-text-secondary"
              data-testid="trade-history-empty"
            >
              {{ t('trade.recent_transactions.no_data') }}
            </div>
          </RuiTabItem>
        </RuiTabItems>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
