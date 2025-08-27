<script setup lang="ts">
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import DateDisplay from '@/components/display/DateDisplay.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useRefWithDebounce } from '@/composables/ref';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import HashLink from '@/modules/common/links/HashLink.vue';
import {
  useHistoryQueryIndicatorSettings,
} from '@/modules/dashboard/history-events/composables/use-history-query-indicator-settings';
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
const { progress } = useHistoryQueryProgress();
const { allTxChainsInfo } = useSupportedChains();
const userId = useLoggedUserIdentifier();
const { dismissalThresholdMs, minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();
const [DefineTimeTooltip, ReuseTimeTooltip] = createReusableTemplate();

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
  if (get(processing)) {
    const progressData = get(progress);
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
  const progressData = get(progress);
  return progressData?.percentage ?? 0;
});

const showMessage = computed<boolean>(() => {
  const status = get(transactionStatus);
  if (!isDefined(status) || get(processing)) {
    return false;
  }

  const now = Date.now();
  const lastQueriedTs = get(lastQueriedTimestamp);
  const minOutOfSyncMs = get(minOutOfSyncPeriodMs);

  // Don't show if not out of sync enough
  if (now - lastQueriedTs < minOutOfSyncMs) {
    return false;
  }

  // Don't show if dismissed recently
  const dismissalMs = get(dismissalThresholdMs);
  const { lastDismissedTs } = get(queryStatus);
  const dismissedRecently = now - lastDismissedTs < dismissalMs;

  return !dismissedRecently;
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
  <DefineTimeTooltip>
    <RuiTooltip
      :open-delay="400"
      persist-on-tooltip-hover
    >
      <template #activator>
        <span class="underline decoration-dotted cursor-help">
          {{ lastQueriedDisplay }}
        </span>
      </template>
      <DateDisplay
        :timestamp="lastQueriedTimestamp"
        hide-tooltip
        milliseconds
      />
    </RuiTooltip>
  </DefineTimeTooltip>

  <div
    v-if="hasTxAccounts && (processingMessage || showMessage)"
    class="w-full px-4 py-2 border-b border-default bg-white dark:bg-[#1E1E1E] text-sm text-rui-text-secondary flex items-center justify-between gap-4"
  >
    <div class="flex items-center gap-2">
      <RuiProgress
        v-if="processingMessage"
        circular
        :value="processingPercentage"
        size="30"
        show-label
        thickness="2"
        color="primary"
      />

      <div
        v-if="processingMessage"
        class="inline gap-2"
      >
        {{ processingMessage }}
        <template v-if="progress?.currentOperationData">
          <i18n-t
            v-if="progress.currentOperationData.type === 'transaction'"
            keypath="dashboard.history_query_indicator.processing_operation_transaction"
            tag="span"
          >
            <template #status>
              {{ progress.currentOperationData.status }}
            </template>
            <template #address>
              <span class="inline-flex items-center gap-1 align-middle ml-1.5 -mt-0.5">
                <ChainIcon
                  v-if="progress.currentOperationData.chain"
                  :chain="progress.currentOperationData.chain"
                  size="1.25rem"
                />
                <HashLink
                  v-if="progress.currentOperationData.address"
                  class="inline-flex align-middle"
                  display-mode="text"
                  :text="progress.currentOperationData.address"
                  :location="progress.currentOperationData.chain"
                />
              </span>
            </template>
          </i18n-t>
          <i18n-t
            v-else-if="progress.currentOperationData.type === 'event'"
            keypath="dashboard.history_query_indicator.processing_operation_event"
            tag="span"
          >
            <template #status>
              {{ progress.currentOperationData.status }}
            </template>
            <template #name>
              <span class="inline-flex items-center gap-1 align-middle ml-1.5 -mt-0.5">
                <LocationIcon
                  v-if="progress.currentOperationData.location"
                  :item="progress.currentOperationData.location"
                  horizontal
                  size="1.25rem"
                  class="-my-2"
                />
                {{ progress.currentOperationData.name }}
              </span>
            </template>
            <template #location>
              {{ progress.currentOperationData.location }}
            </template>
          </i18n-t>
        </template>
      </div>

      <div v-else-if="showMessage">
        <template v-if="justUpdated">
          {{ t('dashboard.history_query_indicator.just_updated') }}
        </template>
        <template v-else-if="isNeverQueried">
          {{ t('dashboard.history_query_indicator.never_queried') }}
        </template>
        <template v-else>
          <i18n-t
            v-if="longQuery"
            keypath="dashboard.history_query_indicator.last_queried_long"
          >
            <template #time>
              <ReuseTimeTooltip />
            </template>
          </i18n-t>
          <i18n-t
            v-if="transactionStatus && transactionStatus.undecodedTxCount === 0"
            keypath="dashboard.history_query_indicator.last_queried"
          >
            <template #time>
              <ReuseTimeTooltip />
            </template>
          </i18n-t>
          <i18n-t
            v-else
            keypath="dashboard.history_query_indicator.incomplete_decoding"
          >
            <template #time>
              <ReuseTimeTooltip />
            </template>
          </i18n-t>
        </template>
      </div>
    </div>

    <div class="flex flex-row gap-2">
      <RuiButton
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
</template>
