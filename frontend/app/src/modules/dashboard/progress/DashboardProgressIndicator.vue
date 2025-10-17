<script setup lang="ts">
import { useRefWithDebounce } from '@/composables/ref';
import BalanceQuerySection from '@/modules/dashboard/progress/components/BalanceQuerySection.vue';
import HistoryQuerySection from '@/modules/dashboard/progress/components/HistoryQuerySection.vue';
import IdleQuerySection from '@/modules/dashboard/progress/components/IdleQuerySection.vue';
import { useUnifiedProgress } from '@/modules/dashboard/progress/composables/use-unified-progress';
import { useMainStore } from '@/store/main';

const { t } = useI18n({ useScope: 'global' });

const justUpdated = ref<boolean>(false);

const { appVersion } = storeToRefs(useMainStore());

const {
  balanceProgress,
  dismissalThresholdMs,
  hasTxAccounts,
  hasUndecodedTransactions,
  historyProgress,
  isNeverQueried,
  lastQueriedDisplay,
  lastQueriedTimestamp,
  longQuery,
  navigateToHistory,
  processing,
  processingMessage,
  processingPercentage,
  queryStatus,
  showIdleMessage,
  transactionStatusSummary,
} = useUnifiedProgress();

const historyStatusDismissedRecently = computed(() => {
  const now = Date.now();
  const dismissalMs = get(dismissalThresholdMs);
  const { lastDismissedTs } = get(queryStatus);
  return now - lastDismissedTs < dismissalMs;
});

const balanceStatusDismissedRecently = computed(() => {
  const now = Date.now();
  const dismissalMs = get(dismissalThresholdMs);
  const { lastBalanceProgressDismissedTs } = get(queryStatus);
  return now - lastBalanceProgressDismissedTs < dismissalMs;
});

function dismissHistoryProgress(): void {
  set(queryStatus, {
    ...get(queryStatus),
    lastDismissedTs: Date.now(),
    lastUsedVersion: get(appVersion),
  });
}

function dismissBalanceProgress(): void {
  set(queryStatus, {
    ...get(queryStatus),
    lastBalanceProgressDismissedTs: Date.now(),
    lastUsedVersion: get(appVersion),
  });
}

const hasHistoryProgress = logicAnd(
  hasTxAccounts,
  historyProgress,
  processing,
);

const showHistoryProgress = logicAnd(
  useRefWithDebounce(logicOr(
    hasHistoryProgress,
    showIdleMessage,
  ), 300),
  logicNot(historyStatusDismissedRecently),
);

const showBalanceProgress = logicAnd(
  useRefWithDebounce(logicAnd(balanceProgress), 300),
  logicNot(balanceStatusDismissedRecently),
);

const showSection = logicOr(
  showHistoryProgress,
  showBalanceProgress,
);

onMounted(async () => {
  if (get(appVersion) === get(queryStatus, 'lastUsedVersion')) {
    return;
  }
  set(queryStatus, {
    lastBalanceProgressDismissedTs: get(queryStatus, 'lastBalanceProgressDismissedTs') || 0,
    lastDismissedTs: get(queryStatus, 'lastDismissedTs') || 0,
    lastUsedVersion: get(appVersion),
  });
  set(justUpdated, true);
});
</script>

<template>
  <Transition
    enter-active-class="transition-all duration-100 ease-out"
    enter-from-class="-translate-y-full opacity-0"
    enter-to-class="translate-y-0 opacity-100"
    leave-active-class="transition-all duration-100 ease-in"
    leave-from-class="translate-y-0 opacity-100"
    leave-to-class="-translate-y-full opacity-0"
  >
    <div
      v-if="showSection"
      class="w-full px-4 py-2 border-b border-default bg-white dark:bg-[#1E1E1E] text-sm text-rui-text-secondary flex items-center justify-between gap-4"
    >
      <div class="flex items-center gap-2">
        <!-- Balance Query Section -->
        <BalanceQuerySection
          v-if="showBalanceProgress && balanceProgress"
          :progress="balanceProgress"
          :processing-message="processingMessage"
          :processing-percentage="processingPercentage"
        />

        <!-- History Query Section -->
        <HistoryQuerySection
          v-else-if="showHistoryProgress && historyProgress"
          :progress="historyProgress"
          :processing-message="processingMessage"
          :processing-percentage="processingPercentage"
        />

        <!-- Idle State Section -->
        <IdleQuerySection
          v-else-if="showIdleMessage"
          :just-updated="justUpdated"
          :is-never-queried="isNeverQueried"
          :long-query="longQuery"
          :has-undecoded-txs="hasUndecodedTransactions"
          :transaction-status="transactionStatusSummary"
          :last-queried-display="lastQueriedDisplay"
          :last-queried-timestamp="lastQueriedTimestamp"
        />
      </div>

      <div class="flex flex-row gap-2">
        <RuiButton
          v-if="!balanceProgress"
          variant="text"
          size="sm"
          color="primary"
          @click="navigateToHistory()"
        >
          {{ t('dashboard.history_query_indicator.go_to_history_events') }}
        </RuiButton>
        <RuiButton
          variant="text"
          icon
          size="sm"
          @click="showBalanceProgress ? dismissBalanceProgress () : dismissHistoryProgress()"
        >
          <RuiIcon
            name="lu-x"
            size="16"
          />
        </RuiButton>
      </div>
    </div>
  </Transition>
</template>
