<script setup lang="ts">
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import {
  useHistoryQueryIndicatorSettings,
} from '@/modules/dashboard/history-events/composables/use-history-query-indicator-settings';
import { useTransactionStatusCheck } from '@/modules/dashboard/history-events/composables/use-transaction-status-check';
import { useHistoryStore } from '@/store/history';
import { useMainStore } from '@/store/main';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { isMajorOrMinorUpdate } from '@/utils/version';

const HUNDRED_EIGHTY_DAYS = 15_552_000_000;

interface QueryStatus {
  lastDismissedTs: number;
  lastUsedVersion: string | null;
}

const justUpdated = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

const historyStore = useHistoryStore();
const { transactionStatusSummary } = storeToRefs(historyStore);
const { appVersion } = storeToRefs(useMainStore());
const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const { allTxChainsInfo } = useSupportedChains();
const userId = useLoggedUserIdentifier();
const { dismissalThresholdMs } = useHistoryQueryIndicatorSettings();
const {
  earliestQueriedTimestamp: lastQueriedTimestamp,
  isNeverQueried,
  isOutOfSync: isOutOfSyncCheck,
  navigateToHistory,
  processing,
} = useTransactionStatusCheck();
const [DefineTimeTooltip, ReuseTimeTooltip] = createReusableTemplate();

const queryStatus = useLocalStorage<QueryStatus>(`${get(userId)}.rotki_query_status`, { lastDismissedTs: 0, lastUsedVersion: null });

const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

const accounts = computed<BlockchainAccount[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

const hasTxAccounts = computed<boolean>(() => {
  const { hasEvmAccounts = false, hasExchangesAccounts = false } = get(transactionStatusSummary) ?? {};

  // Return true if user has exchange accounts
  if (hasExchangesAccounts) {
    return true;
  }

  // Check for EVM accounts
  if (!hasEvmAccounts) {
    return false;
  }
  const filteredChains = get(txChainIds);
  return get(accounts).some(({ chain }) => filteredChains.includes(chain));
});

const lastQueriedDisplay = useTimeAgo(lastQueriedTimestamp);

const processingMessage = computed<string>(() => {
  if (get(processing)) {
    return t('dashboard.history_query_indicator.processing');
  }
  return '';
});

const showMessage = computed<boolean>(() => {
  const status = get(transactionStatusSummary);
  if (!isDefined(status) || get(processing)) {
    return false;
  }

  // Use the composable's out of sync check
  if (!get(isOutOfSyncCheck)) {
    return false;
  }

  // Don't show if dismissed recently
  const dismissalMs = get(dismissalThresholdMs);
  const { lastDismissedTs } = get(queryStatus);
  const dismissedRecently = Date.now() - lastDismissedTs < dismissalMs;

  return !dismissedRecently;
});

const longQuery = computed<boolean>(() => {
  const status = get(transactionStatusSummary);
  const now = Date.now();
  const lastQueried = get(lastQueriedTimestamp);
  return isDefined(status) && status.undecodedTxCount === 0 && now - lastQueried > HUNDRED_EIGHTY_DAYS;
});

function dismiss(): void {
  set(queryStatus, {
    lastDismissedTs: Date.now(),
    lastUsedVersion: get(appVersion),
  });
}

onMounted(async () => {
  const currentVersion = get(appVersion);
  const lastVersion = get(queryStatus, 'lastUsedVersion');

  if (currentVersion === lastVersion) {
    return;
  }

  set(queryStatus, {
    lastDismissedTs: get(queryStatus, 'lastDismissedTs'),
    lastUsedVersion: currentVersion,
  });

  // Only set justUpdated to true for major/minor updates, not patch releases
  if (isMajorOrMinorUpdate(currentVersion, lastVersion)) {
    set(justUpdated, true);
  }
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
    class="w-full px-4 py-2 border-b border-default bg-white dark:bg-[#1E1E1E] text-sm text-rui-text-secondary flex items-center justify-between"
  >
    <div class="flex items-center gap-2">
      <RuiProgress
        v-if="processingMessage"
        circular
        variant="indeterminate"
        size="16"
        thickness="2"
        color="primary"
      />

      <div v-if="processingMessage">
        {{ processingMessage }}
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
            v-if="transactionStatusSummary && transactionStatusSummary.undecodedTxCount === 0"
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
