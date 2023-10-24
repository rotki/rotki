<script setup lang="ts">
import {
  type Eth2DailyStatsPayload,
  type Eth2StakingFilter,
  type EthStakingPayload,
  type EthStakingPeriod
} from '@rotki/common/lib/staking/eth2';
import { type ComputedRef } from 'vue';
import { EthStaking } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';

const module = Module.ETH2;
const section = Section.STAKING_ETH2;

const period: Ref<EthStakingPeriod> = ref({});
const selection: Ref<Eth2StakingFilter> = ref({
  accounts: [],
  validators: []
});

const store = useEth2StakingStore();
const { details } = storeToRefs(store);
const { fetchStakingDetails } = store;

const { isModuleEnabled } = useModules();

const enabled = isModuleEnabled(module);
const {
  dailyStats,
  fetchDailyStats,
  syncStakingStats,
  dailyStatsLoading,
  pagination
} = useEth2DailyStats();
const { rewards, fetchRewards, loading: rewardsLoading } = useEth2Rewards();

const { isLoading, shouldShowLoadingScreen, setStatus } = useStatusStore();

const detailsLoading = shouldShowLoadingScreen(section);
const primaryRefreshing = isLoading(section);

const { eth2Validators } = storeToRefs(useEthAccountsStore());

const ownership = computed(() => {
  const ownership: Record<string, string> = {};
  for (const { validatorIndex, ownershipPercentage } of get(eth2Validators)
    .entries) {
    ownership[validatorIndex] = ownershipPercentage;
  }
  return ownership;
});

const validatorFilter: ComputedRef<EthStakingPayload> = computed(() => {
  const { accounts, validators } = get(selection);
  return {
    addresses: accounts.map(({ address }) => address),
    validatorIndices: validators.map(({ validatorIndex }) => validatorIndex)
  };
});

const dailyStatsPayload: ComputedRef<Eth2DailyStatsPayload> = computed(() => {
  const payload = get(pagination);
  const { fromTimestamp, toTimestamp } = get(period);
  return {
    ...payload,
    fromTimestamp,
    toTimestamp
  };
});

const premium = usePremium();
const { t } = useI18n();

const refreshStats = async (userInitiated: boolean): Promise<void> => {
  await fetchDailyStats(get(dailyStatsPayload));
  const success = await syncStakingStats(userInitiated);
  if (success) {
    // We unref here to make sure that we use the latest pagination
    await fetchDailyStats(get(dailyStatsPayload));
  }
};

const refresh = async (userInitiated = false): Promise<void> => {
  const filterBy = get(validatorFilter);
  await Promise.allSettled([
    refreshStats(userInitiated),
    fetchRewards(filterBy),
    fetchStakingDetails(userInitiated, { ...filterBy, ...get(period) })
  ]);
};

onMounted(async () => {
  if (get(enabled)) {
    await refresh(false);
  }
});

onUnmounted(() => {
  store.$reset();
  setStatus({
    section,
    status: Status.NONE
  });
});

watch(validatorFilter, async filter => {
  await Promise.allSettled([
    fetchRewards({ ...filter, ...get(period) }),
    fetchStakingDetails(false, filter)
  ]);
});

watch(period, async period => {
  await fetchRewards({ ...get(validatorFilter), ...period });
});

const refreshClick = async () => {
  await refresh();
  if (isDefined(pagination)) {
    set(pagination, {
      ...get(pagination),
      onlyCache: false
    });
  }
};
</script>

<template>
  <div>
    <NoPremiumPlaceholder v-if="!premium" :text="t('eth2_page.no_premium')" />
    <ModuleNotActive v-else-if="!enabled" :modules="[module]" />

    <TablePageLayout
      v-else
      :title="[t('navigation_menu.staking'), t('staking.eth2')]"
      child
    >
      <template #buttons>
        <div class="flex items-center gap-3">
          <ActiveModules :modules="[module]" />

          <RuiTooltip open-delay="400">
            <template #activator>
              <RuiButton
                variant="outlined"
                color="primary"
                :loading="primaryRefreshing || dailyStatsLoading"
                @click="refreshClick()"
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
        :secondary-refreshing="false"
        :validators="eth2Validators.entries"
        :filter="selection"
        :period="period"
        :rewards="rewards"
        :rewards-loading="rewardsLoading"
        :eth2-details="details"
        :eth2-details-loading="detailsLoading"
        :eth2-stats="dailyStats"
        :eth2-stats-loading="dailyStatsLoading"
        :ownership="ownership"
        :pagination="pagination"
        @update:stats-pagination="pagination = $event"
      >
        <template #selection>
          <EthValidatorFilter
            v-model="selection"
            @update:period="period = $event"
          />
        </template>
      </EthStaking>
    </TablePageLayout>
  </div>
</template>
