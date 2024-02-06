<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { EthStaking } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { useBlockchainBalances } from '@/composables/blockchain/balances';
import type { EthStakingFilter, EthStakingPeriod } from '@rotki/common/lib/staking/eth2';

const module = Module.ETH2;
const section = Section.STAKING_ETH2;

const period = ref<EthStakingPeriod>();
const selection = ref<EthStakingFilter>({
  validators: [],
});

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
  refreshStats,
} = useEth2DailyStats();

const { isLoading, setStatus } = useStatusStore();

const primaryRefreshing = isLoading(section);

const accountsStore = useEthAccountsStore();
const { eth2Validators } = storeToRefs(accountsStore);
const { stakingBalances } = storeToRefs(useEthBalancesStore());
const { fetchBlockchainBalances } = useBlockchainBalances();

const ownership = computed<Record<string, string>>(() => {
  const ownership: Record<string, string> = {};
  for (const { index, ownershipPercentage } of get(eth2Validators).entries) {
    if (ownershipPercentage)
      ownership[index] = ownershipPercentage;
  }
  return ownership;
});

const premium = usePremium();
const { t } = useI18n();

async function refresh(userInitiated = false): Promise<void> {
  const refreshValidators = async () => {
    await fetchBlockchainBalances({
      ignoreCache: true,
      blockchain: Blockchain.ETH2,
    });
    await accountsStore.fetchEth2Validators();
  };

  const validatorRefresh: Promise<void>[] = (userInitiated ? [refreshValidators()] : []);

  await Promise.allSettled([
    refreshStats(userInitiated),
    refreshPerformance(userInitiated),
    ...validatorRefresh,
  ]);
}

onMounted(async () => {
  if (get(enabled))
    await refresh(false);
});

onUnmounted(() => {
  setStatus({
    section,
    status: Status.NONE,
  });
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
                :loading="primaryRefreshing || dailyStatsLoading"
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
        :refreshing="primaryRefreshing"
        :validators="eth2Validators.entries"
        :balances="stakingBalances"
        :filter="selection"
        :period.sync="period"
        :performance="performance"
        :performance-loading="performanceLoading"
        :performance-pagination.sync="performancePagination"
        :stats="dailyStats"
        :stats-loading="dailyStatsLoading"
        :stats-pagination.sync="pagination"
        :ownership="ownership"
      >
        <template #selection>
          <EthValidatorFilter
            v-model="selection"
            :period.sync="period"
          />
        </template>
      </EthStaking>
    </TablePageLayout>
  </div>
</template>
