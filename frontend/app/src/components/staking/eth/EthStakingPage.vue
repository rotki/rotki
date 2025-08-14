<script setup lang="ts">
import { type BigNumber, Blockchain, type Eth2ValidatorEntry, type Eth2Validators, type EthStakingCombinedFilter, type EthStakingFilter, Zero } from '@rotki/common';
import dayjs from 'dayjs';
import { omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import EthStakingPagePlaceholder from '@/components/staking/eth/EthStakingPagePlaceholder.vue';
import EthValidatorFilter from '@/components/staking/eth/EthValidatorFilter.vue';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';
import { usePremium } from '@/composables/premium';
import { useModules } from '@/composables/session/modules';
import { useEth2Staking } from '@/composables/staking/eth2/eth2';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { EthStaking } from '@/premium/premium';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useSessionAuthStore } from '@/store/session/auth';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { nonEmptyProperties } from '@/utils/data';
import { logger } from '@/utils/logging';

const module = Module.ETH2;
const performanceSection = Section.STAKING_ETH2;

const filter = ref<EthStakingCombinedFilter>();
const selection = ref<EthStakingFilter>({
  validators: [],
});

const total = ref<BigNumber>(Zero);

const { username } = storeToRefs(useSessionAuthStore());

function createLastRefreshStorage(username: string): Ref<number> {
  return useSessionStorage(`rotki.staking.last_refresh.${username}`, 0);
}

const lastRefresh = createLastRefreshStorage(get(username));

const { pagination: performancePagination, performance, performanceLoading, refreshPerformance } = useEth2Staking();

const { isModuleEnabled } = useModules();

const enabled = isModuleEnabled(module);

const { isLoading } = useStatusStore();
const { useIsTaskRunning } = useTaskStore();

const { isFirstLoad } = useStatusUpdater(performanceSection);

const performanceRefreshing = isLoading(performanceSection);
const blockProductionLoading = useIsTaskRunning(TaskType.QUERY_ONLINE_EVENTS, {
  queryType: OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
});

const refreshing = logicOr(
  performanceRefreshing,
  isLoading(Section.BLOCKCHAIN, Blockchain.ETH2),
  blockProductionLoading,
);

const { getEth2Validators } = useBlockchainAccountsApi();
const { fetchEthStakingValidators } = useEthStaking();
const { ethStakingValidators, stakingValidatorsLimits } = storeToRefs(useBlockchainValidatorsStore());
const { fetchBlockchainBalances } = useBlockchainBalances();

const premium = usePremium();
const { t } = useI18n({ useScope: 'global' });

async function refresh(userInitiated = false): Promise<void> {
  const refreshValidators = async (userInitiated: boolean) => {
    await fetchBlockchainBalances({
      blockchain: Blockchain.ETH2,
      ignoreCache: userInitiated || isFirstLoad(),
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

  await updatePerformance(userInitiated);
  set(lastRefresh, dayjs().unix());
}

function setTotal(validators?: Eth2Validators['entries']) {
  const publicKeys = validators?.map((validator: Eth2ValidatorEntry) => validator.publicKey);
  const stakingValidators = get(ethStakingValidators);
  const selectedValidators = publicKeys
    ? stakingValidators.filter(validator => publicKeys.includes(validator.publicKey))
    : stakingValidators;
  const totalStakedAmount = selectedValidators.reduce((sum, item) => sum.plus(item.amount), Zero);
  set(total, totalStakedAmount);
}

watch([selection, filter], async () => {
  await fetchValidatorsWithFilter();
});

async function fetchValidatorsWithFilter() {
  const filterVal = get(filter);
  const selectionVal = get(selection);
  const statusFilter = filterVal ? omit(filterVal, ['fromTimestamp', 'toTimestamp']) : {};
  const accounts
    = 'accounts' in selectionVal
      ? { addresses: selectionVal.accounts.map(account => account.address) }
      : { validatorIndices: selectionVal.validators.map((validator: Eth2ValidatorEntry) => validator.index) };

  const combinedFilter = nonEmptyProperties({ ...statusFilter, ...accounts });

  const validators = isEmpty(combinedFilter) ? undefined : (await getEth2Validators(combinedFilter)).entries;
  setTotal(validators);
}

onBeforeMount(async () => {
  if (get(enabled))
    await refresh(false);

  await fetchValidatorsWithFilter();
});
</script>

<template>
  <div>
    <EthStakingPagePlaceholder v-if="!premium" />
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
                  <RuiIcon name="lu-refresh-ccw" />
                </template>
                {{ t('common.refresh') }}
              </RuiButton>
            </template>
            {{ t('premium_components.staking.refresh') }}
          </RuiTooltip>
        </div>
      </template>

      <EthStaking
        v-model:performance-pagination="performancePagination"
        v-model:filter="filter"
        :refreshing="refreshing"
        :total="total"
        :accounts="selection"
        :performance="performance"
        :performance-loading="performanceLoading"
      >
        <template #selection>
          <EthValidatorFilter
            v-model="selection"
            v-model:filter="filter"
          />
        </template>
      </EthStaking>
    </TablePageLayout>
  </div>
</template>
