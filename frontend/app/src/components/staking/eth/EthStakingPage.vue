<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { objectOmit } from '@vueuse/core';
import { isEmpty } from 'lodash-es';
import dayjs from 'dayjs';
import { EthStaking } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { OnlineHistoryEventsQueryType } from '@/types/history/events';
import type { BigNumber } from '@rotki/common';
import type { GeneralAccount } from '@rotki/common/lib/account';
import type {
  Eth2ValidatorEntry,
  Eth2Validators,
  EthStakingCombinedFilter,
  EthStakingFilter,
} from '@rotki/common/lib/staking/eth2';

const module = Module.ETH2;
const performanceSection = Section.STAKING_ETH2;
const statsSection = Section.STAKING_ETH2_STATS;

const filter = ref<EthStakingCombinedFilter>();
const selection = ref<EthStakingFilter>({
  validators: [],
});

const total = ref<BigNumber>(Zero);

const lastRefresh = useSessionStorage('rotki.staking.last_refresh', 0);

const {
  performance,
  performanceLoading,
  pagination: performancePagination,
  refreshPerformance,
} = useEth2Staking();

const { isModuleEnabled } = useModules();

const enabled = isModuleEnabled(module);
const {
  dailyStats,
  dailyStatsLoading,
  pagination,
  refresh: reloadStats,
  refreshStats,
} = useEth2DailyStats();

const { isLoading } = useStatusStore();
const { isTaskRunning } = useTaskStore();

const performanceRefreshing = isLoading(performanceSection);
const statsRefreshing = isLoading(statsSection);
const blockProductionLoading = isTaskRunning(TaskType.QUERY_ONLINE_EVENTS, {
  queryType: OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
});

const refreshing = logicOr(
  performanceRefreshing,
  isLoading(Section.BLOCKCHAIN, Blockchain.ETH2),
  blockProductionLoading,
);

const { getEth2Validators } = useBlockchainAccountsApi();
const accountsStore = useEthAccountsStore();
const { eth2Validators } = storeToRefs(accountsStore);
const { stakingBalances } = storeToRefs(useEthBalancesStore());
const { fetchBlockchainBalances } = useBlockchainBalances();

const premium = usePremium();
const { t } = useI18n();

function shouldRefreshDailyStats() {
  const threshold = dayjs().subtract(1, 'hour').unix();
  return get(lastRefresh) < threshold;
}

async function refresh(userInitiated = false): Promise<void> {
  const refreshValidators = async (userInitiated: boolean) => {
    await fetchBlockchainBalances({
      ignoreCache: userInitiated,
      blockchain: Blockchain.ETH2,
    });
    await accountsStore.fetchEth2Validators();
  };

  const updatePerformance = async (userInitiated = false): Promise<void> => {
    await refreshPerformance(userInitiated);
    // if the number of validators is bigger than the total entries in performance
    // force a refresh of performance to pick the missing performance entries.
    const totalValidators = get(eth2Validators).entriesFound;
    const totalPerformanceEntries = get(performance).entriesTotal;
    if (totalValidators > totalPerformanceEntries) {
      logger.log(`forcing refresh validators: ${totalValidators}/performance: ${totalPerformanceEntries}`);
      await refreshPerformance(true);
    }
  };

  await refreshValidators(userInitiated);
  setTotal(get(eth2Validators));

  const statsRefresh: Promise<void>[] = (
    (!get(statsRefreshing) && shouldRefreshDailyStats())
      ? [refreshStats(userInitiated)]
      : [reloadStats()]
  );
  await Promise.allSettled([
    updatePerformance(userInitiated),
    ...statsRefresh,
  ]);
  set(lastRefresh, dayjs().unix());
}

function setTotal(validators: Eth2Validators) {
  const publicKeys = validators.entries.map((validator: Eth2ValidatorEntry) => validator.publicKey);
  const totalStakedAmount = get(stakingBalances)
    .filter(x => publicKeys.includes(x.publicKey))
    .reduce((sum, item) => sum.plus(item.amount), Zero);
  set(total, totalStakedAmount);
}

watch([selection, filter] as const, async ([selection, filter]) => {
  const statusFilter = filter ? objectOmit(filter, ['fromTimestamp', 'toTimestamp']) : {};
  const accounts = 'accounts' in selection
    ? { addresses: selection.accounts.map((account: GeneralAccount) => account.address) }
    : { validatorIndices: selection.validators.map((validator: Eth2ValidatorEntry) => validator.index) };

  const combinedFilter = nonEmptyProperties({ ...statusFilter, ...accounts });

  const validators = isEmpty(combinedFilter) ? get(eth2Validators) : await getEth2Validators(combinedFilter);
  setTotal(validators);
});

onMounted(async () => {
  if (get(enabled))
    await refresh(false);
  setTotal(get(eth2Validators));
});
</script>

<template>
  <div>
    <NoPremiumPlaceholder
      v-if="!premium"
      :text="t('eth2_page.no_premium')"
    />
    <ModuleNotActive
      v-else-if="!enabled"
      :modules="[module]"
    />

    <TablePageLayout
      v-else
      :title="[t('navigation_menu.staking'), t('staking.eth2')]"
      child
    >
      <template #buttons>
        <div class="flex items-center gap-3">
          <ActiveModules :modules="[module]" />

          <RuiTooltip :open-delay="400">
            <template #activator>
              <RuiButton
                variant="outlined"
                color="primary"
                :loading="refreshing"
                @click="refresh(true)"
              >
                <template #prepend>
                  <RuiIcon name="refresh-line" />
                </template>
                {{ t('common.refresh') }}
              </RuiButton>
            </template>
            {{ t('premium_components.staking.refresh') }}
          </RuiTooltip>
        </div>
      </template>

      <EthStaking
        :refreshing="performanceRefreshing"
        :total="total"
        :accounts="selection"
        :filter.sync="filter"
        :performance="performance"
        :performance-loading="performanceLoading"
        :performance-pagination.sync="performancePagination"
        :stats="dailyStats"
        :stats-loading="dailyStatsLoading"
        :stats-pagination.sync="pagination"
      >
        <template #selection>
          <EthValidatorFilter
            v-model="selection"
            :filter.sync="filter"
          />
        </template>
      </EthStaking>
    </TablePageLayout>
  </div>
</template>
