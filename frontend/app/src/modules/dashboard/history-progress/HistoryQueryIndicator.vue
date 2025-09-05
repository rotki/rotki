<script setup lang="ts">
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { useRefWithDebounce } from '@/composables/ref';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import {
  useHistoryQueryIndicatorSettings,
} from '@/modules/dashboard/history-events/composables/use-history-query-indicator-settings';
import BalanceQuerySection from '@/modules/dashboard/history-progress/components/BalanceQuerySection.vue';
import HistoryQuerySection from '@/modules/dashboard/history-progress/components/HistoryQuerySection.vue';
import IdleQuerySection from '@/modules/dashboard/history-progress/components/IdleQuerySection.vue';
import { useBalanceQueryProgress } from '@/modules/dashboard/history-progress/composables/use-balance-query-progress';
import { useHistoryQueryProgress } from '@/modules/dashboard/history-progress/composables/use-history-query-progress';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/store/history';
import { useMainStore } from '@/store/main';
import { hasAccountAddress } from '@/utils/blockchain/accounts';

const HUNDRED_EIGHTY_DAYS = 15_552_000_000;

interface QueryStatus {
  lastDismissedTs: number;
  lastUsedVersion: string | null;
}

const justUpdated = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

const historyStore = useHistoryStore();
const { evmTransactionStatus: transactionStatus } = storeToRefs(historyStore);
const { appVersion } = storeToRefs(useMainStore());
const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const router = useRouter();
const { processing: rawProcessing } = useHistoryEventsStatus();
const processing = useRefWithDebounce(rawProcessing, 400);
const { progress: historyProgress } = useHistoryQueryProgress();
const { balanceProgress, isBalanceQuerying } = useBalanceQueryProgress();
const { allTxChainsInfo } = useSupportedChains();
const userId = useLoggedUserIdentifier();
const { dismissalThresholdMs, minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();

const queryStatus = useLocalStorage<QueryStatus>(`${get(userId)}.rotki_query_status`, { lastDismissedTs: 0, lastUsedVersion: null });

const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

const accounts = computed<BlockchainAccount[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

const hasTxAccounts = computed<boolean>(() => {
  const { hasEvmAccounts = false } = get(transactionStatus) ?? {};
  if (!hasEvmAccounts) {
    return false;
  }
  const filteredChains = get(txChainIds);
  return get(accounts).some(({ chain }) => filteredChains.includes(chain));
});

const lastQueriedTimestamp = computed<number>(() => {
  const status = get(transactionStatus);
  if (!status || status.lastQueriedTs === 0)
    return 0;

  // Convert seconds to milliseconds for useTimeAgo
  return status.lastQueriedTs * 1000;
});

const lastQueriedDisplay = useTimeAgo(lastQueriedTimestamp);

const processingMessage = computed<string>(() => {
  // Prioritize balance/token detection over history events
  const balanceProgressData = get(balanceProgress);
  if (balanceProgressData && balanceProgressData.currentOperation) {
    return balanceProgressData.currentOperation;
  }

  // Only show history events progress if no balance queries are running
  if (get(processing) && !get(isBalanceQuerying)) {
    const progressData = get(historyProgress);
    if (progressData && progressData.totalSteps > 0) {
      return t('dashboard.history_query_indicator.processing_with_progress', {
        current: progressData.currentStep,
        total: progressData.totalSteps,
      });
    }
    return t('dashboard.history_query_indicator.processing');
  }
  return '';
});

const processingPercentage = computed<number>(() => {
  // Prioritize balance/token detection percentage
  const balanceProgressData = get(balanceProgress);
  if (balanceProgressData) {
    return balanceProgressData.percentage;
  }

  // Use history progress if no balance queries
  if (!get(isBalanceQuerying)) {
    const progressData = get(historyProgress);
    return progressData?.percentage ?? 0;
  }

  return 0;
});

const showIdleMessage = computed<boolean>(() => {
  const status = get(transactionStatus);
  if (!isDefined(status)) {
    return false;
  }

  const now = Date.now();
  const lastQueriedTs = get(lastQueriedTimestamp);
  const minOutOfSyncMs = get(minOutOfSyncPeriodMs);

  // Don't show if not out of sync enough
  return now - lastQueriedTs >= minOutOfSyncMs;
});

const dismissedRecently = computed(() => {
  // Don't show if dismissed recently
  const now = Date.now();
  const dismissalMs = get(dismissalThresholdMs);
  const { lastDismissedTs } = get(queryStatus);
  return now - lastDismissedTs < dismissalMs;
});

const isNeverQueried = computed<boolean>(() => {
  const status = get(transactionStatus);
  return isDefined(status) && status.lastQueriedTs === 0;
});

const longQuery = computed<boolean>(() => {
  const status = get(transactionStatus);
  const now = Date.now();
  return isDefined(status) && status.undecodedTxCount === 0 && now - status.lastQueriedTs > HUNDRED_EIGHTY_DAYS;
});

function navigateToHistory(): void {
  router.push('/history');
}

function dismiss(): void {
  set(queryStatus, {
    lastDismissedTs: Date.now(),
    lastUsedVersion: get(appVersion),
  });
}

const hasHistoryProgress = logicAnd(
  hasTxAccounts,
  historyProgress,
  processing,
);

const showSection = useRefWithDebounce(
  logicAnd(
    logicOr(
      hasHistoryProgress,
      balanceProgress,
      showIdleMessage,
    ),
    logicNot(dismissedRecently),
  ),
  300,
);

onMounted(async () => {
  if (get(appVersion) === get(queryStatus, 'lastUsedVersion')) {
    return;
  }
  set(queryStatus, {
    lastDismissedTs: get(queryStatus, 'lastDismissedTs'),
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
          v-if="balanceProgress"
          :progress="balanceProgress"
          :processing-message="processingMessage"
          :processing-percentage="processingPercentage"
        />

        <!-- History Query Section -->
        <HistoryQuerySection
          v-else-if="!isBalanceQuerying && historyProgress"
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
          :transaction-status="transactionStatus"
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
          @click="dismiss()"
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
