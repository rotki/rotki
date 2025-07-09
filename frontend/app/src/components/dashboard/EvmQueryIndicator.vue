<script setup lang="ts">
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/store/history';
import { hasAccountAddress } from '@/utils/blockchain/accounts';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const historyStore = useHistoryStore();
const { evmTransactionStatus } = storeToRefs(historyStore);

const loading = ref(false);
const { processing } = useHistoryEventsStatus();

const lastQueriedDisplay = computed(() => {
  const status = get(evmTransactionStatus);
  if (!status || status.lastQueriedTs === 0)
    return null;

  // Convert seconds to milliseconds for useTimeAgo
  const timestampMs = status.lastQueriedTs * 1000;
  return useTimeAgo(timestampMs);
});

const processingMessage = computed(() => {
  if (get(processing)) {
    return t('dashboard.evm_query_indicator.processing');
  }
  return '';
});

const showMessage = computed(() => {
  const status = get(evmTransactionStatus);
  return status && !get(processing);
});

const isNeverQueried = computed(() => {
  const status = get(evmTransactionStatus);
  return status && status.lastQueriedTs === 0;
});

function navigateToHistory() {
  router.push('/history');
}

const { allTxChainsInfo } = useSupportedChains();
const txChainIds = useArrayMap(allTxChainsInfo, x => x.id);
const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const accounts = computed<BlockchainAccount[]>(() =>
  Object.values(get(accountsPerChain))
    .flatMap(x => x)
    .filter(hasAccountAddress),
);

const hasTxAccounts = computed(() => {
  const filteredChains = get(txChainIds);
  return get(accounts).some(({ chain }) => filteredChains.includes(chain));
});

const [DefineTimeTooltip, ReuseTimeTooltip] = createReusableTemplate();
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
        :timestamp="evmTransactionStatus?.lastQueriedTs ? evmTransactionStatus.lastQueriedTs * 1000 : 0"
        hide-tooltip
        milliseconds
      />
    </RuiTooltip>
  </DefineTimeTooltip>

  <div
    v-if="hasTxAccounts && (processingMessage || showMessage) && !loading"
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
        <template v-if="isNeverQueried">
          {{ t('dashboard.evm_query_indicator.never_queried') }}
        </template>
        <template v-else>
          <i18n-t
            v-if="evmTransactionStatus && !evmTransactionStatus.pendingDecode"
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

    <RuiButton
      variant="text"
      size="sm"
      color="primary"
      @click="navigateToHistory()"
    >
      {{ t('dashboard.evm_query_indicator.go_to_history_events') }}
    </RuiButton>
  </div>
</template>
