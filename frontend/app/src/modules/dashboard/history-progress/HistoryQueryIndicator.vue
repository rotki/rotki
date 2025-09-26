<script setup lang="ts">
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useRefWithDebounce } from '@/composables/ref';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import {
  useHistoryQueryIndicatorSettings,
} from '@/modules/dashboard/progress/composables/use-history-query-indicator-settings';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
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
const { evmTransactionStatus: transactionStatus } = storeToRefs(historyStore);
const { appVersion } = storeToRefs(useMainStore());
const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const router = useRouter();
const { processing: rawProcessing } = useHistoryEventsStatus();
const processing = useRefWithDebounce(rawProcessing, 400);
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
    return t('dashboard.history_query_indicator.processing');
  }
  return '';
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
