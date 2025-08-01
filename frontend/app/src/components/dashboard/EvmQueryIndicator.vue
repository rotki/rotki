<script setup lang="ts">
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/store/history';
import { useMainStore } from '@/store/main';
import { hasAccountAddress } from '@/utils/blockchain/accounts';

interface QueryStatus {
  lastDismissedTs: number;
  lastUsedVersion: string | null;
}

const DISMISS_THRESHOLD_MS = 21_600_000; // 6 hours

const justUpdated = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

const historyStore = useHistoryStore();
const { evmTransactionStatus: transactionStatus } = storeToRefs(historyStore);
const { appVersion } = storeToRefs(useMainStore());
const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const router = useRouter();
const { processing } = useHistoryEventsStatus();
const { allTxChainsInfo } = useSupportedChains();
const userId = useLoggedUserIdentifier();
const [DefineTimeTooltip, ReuseTimeTooltip] = createReusableTemplate();

const queryStatus = useLocalStorage<QueryStatus>(`${get(userId)}.rotki_query_status`, { lastDismissedTs: 0, lastUsedVersion: null });

const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);

const accounts = computed<BlockchainAccount[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

const hasTxAccounts = computed<boolean>(() => {
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
    return t('dashboard.evm_query_indicator.processing');
  }
  return '';
});

const showMessage = computed<boolean>(() => {
  const { lastDismissedTs } = get(queryStatus);
  const dismissedRecently = Date.now() - lastDismissedTs < DISMISS_THRESHOLD_MS;
  const status = get(transactionStatus);
  return !dismissedRecently && isDefined(status) && !get(processing);
});

const isNeverQueried = computed<boolean>(() => {
  const status = get(transactionStatus);
  return isDefined(status) && status.lastQueriedTs === 0;
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
          {{ t('dashboard.evm_query_indicator.just_updated') }}
        </template>
        <template v-else-if="isNeverQueried">
          {{ t('dashboard.evm_query_indicator.never_queried') }}
        </template>
        <template v-else>
          <i18n-t
            v-if="transactionStatus && !transactionStatus.pendingDecode"
            keypath="dashboard.evm_query_indicator.last_queried"
          >
            <template #time>
              <ReuseTimeTooltip />
            </template>
          </i18n-t>
          <i18n-t
            v-else
            keypath="dashboard.evm_query_indicator.incomplete_decoding"
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
        {{ t('dashboard.evm_query_indicator.go_to_history_events') }}
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
