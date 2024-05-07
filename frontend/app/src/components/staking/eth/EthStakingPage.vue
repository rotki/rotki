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
import type {
  Eth2ValidatorEntry,
  Eth2Validators,
  EthStakingCombinedFilter,
  EthStakingFilter,
} from '@rotki/common/lib/staking/eth2';

const module = Module.ETH2;
const performanceSection = Section.STAKING_ETH2;
const statsSection = Section.STAKING_ETH2_STATS;

const filter = ref<EthStakingCombinedFilter>({
  status: 'active',
});
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

const { isFirstLoad } = useStatusUpdater(performanceSection);

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
const { fetchEthStakingValidators } = useEthStaking();
const { ethStakingValidators, stakingValidatorsLimits } = storeToRefs(useBlockchainStore());
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
      ignoreCache: userInitiated || isFirstLoad(),
      blockchain: Blockchain.ETH2,
    });
    await fetchEthStakingValidators();
  };

  const updatePerformance = async (userInitiated = false): Promise<void> => {
    await refreshPerformance(userInitiated);
    // if the number of validators is bigger than the total entries in performance
    // force a refresh of performance to pick the missing performance entries.
    const totalValidators = get(stakingValidatorsLimits)?.total ?? 0;
    const totalPerformanceEntries = get(performance).entriesTotal;
    if (totalValidators > totalPerformanceEntries) {
      logger.log(`forcing refresh validators: ${totalValidators}/performance: ${totalPerformanceEntries}`);
      await refreshPerformance(true);
    }
  };

  await refreshValidators(userInitiated);
  setTotal();

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

function setTotal(validators?: Eth2Validators['entries']) {
  const publicKeys = validators?.map((validator: Eth2ValidatorEntry) => validator.publicKey);
  const stakingValidators = get(ethStakingValidators);
  const selectedValidators = publicKeys
    ? stakingValidators.filter(validator => publicKeys.includes(validator.data.publicKey))
    : stakingValidators;
  const totalStakedAmount = selectedValidators
    .reduce((sum, item) => sum.plus(item.amount), Zero);
  set(total, totalStakedAmount);
}

watch([selection, filter], async () => {
  await fetchValidatorsWithFilter();
});

async function fetchValidatorsWithFilter() {
  const filterVal = get(filter);
  const selectionVal = get(selection);
  const statusFilter = filterVal ? objectOmit(filterVal, ['fromTimestamp', 'toTimestamp']) : {};
  const accounts = 'accounts' in selectionVal
    ? { addresses: selectionVal.accounts.map(account => account.address) }
    : { validatorIndices: selectionVal.validators.map((validator: Eth2ValidatorEntry) => validator.index) };

  const combinedFilter = nonEmptyProperties({ ...statusFilter, ...accounts });

  const validators = isEmpty(combinedFilter) ? undefined : (await getEth2Validators(combinedFilter)).entries;
  setTotal(validators);
};

onBeforeMount(async () => {
  if (get(enabled))
    await refresh(false);

  await fetchValidatorsWithFilter();
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
        :refreshing="refreshing"
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
