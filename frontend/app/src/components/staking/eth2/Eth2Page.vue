<script setup lang="ts">
import {
  type Eth2StakingFilter,
  type EthStakingPayload
} from '@rotki/common/lib/staking/eth2';
import { type ComputedRef } from 'vue';
import { Eth2Staking } from '@/premium/premium';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';

const module = Module.ETH2;

const defaultSelection = () => ({
  accounts: [],
  validators: []
});

const selection: Ref<Eth2StakingFilter> = ref(defaultSelection());
const filterType: Ref<'address' | 'key'> = ref('key');

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

const { isLoading, shouldShowLoadingScreen } = useStatusStore();

const detailsLoading = shouldShowLoadingScreen(Section.STAKING_ETH2);
const primaryRefreshing = isLoading(Section.STAKING_ETH2);

const { eth2Validators } = storeToRefs(useEthAccountsStore());

const ownership = computed(() => {
  const ownership: Record<string, string> = {};
  for (const { validatorIndex, ownershipPercentage } of get(eth2Validators)
    .entries) {
    ownership[validatorIndex] = ownershipPercentage;
  }
  return ownership;
});

const filter: ComputedRef<EthStakingPayload> = computed(() => {
  const { accounts, validators } = get(selection);
  return {
    addresses: accounts.map(({ address }) => address),
    validatorIndices: validators.map(({ validatorIndex }) => validatorIndex)
  };
});

const premium = usePremium();
const { t, tc } = useI18n();

const refreshStats = async (userInitiated: boolean): Promise<void> => {
  await fetchDailyStats(get(pagination));
  const success = await syncStakingStats(userInitiated);
  if (success) {
    // We unref here to make sure that we use the latest pagination
    await fetchDailyStats(get(pagination));
  }
};

const refresh = async (userInitiated = false): Promise<void> => {
  const filterBy = get(filter);
  await Promise.allSettled([
    refreshStats(userInitiated),
    fetchRewards(filterBy),
    fetchStakingDetails(userInitiated, filterBy)
  ]);
};

onMounted(async () => {
  if (get(enabled)) {
    await refresh(false);
  }
});

onUnmounted(() => {
  store.$reset();
});

watch(filter, async filter => {
  await Promise.allSettled([
    fetchRewards(filter),
    fetchStakingDetails(false, filter)
  ]);
});

watch(filterType, () => set(selection, defaultSelection()));
</script>

<template>
  <div>
    <no-premium-placeholder
      v-if="!premium"
      :text="tc('eth2_page.no_premium')"
    />
    <module-not-active v-else-if="!enabled" :modules="[module]" />

    <eth2-staking
      v-else
      :refreshing="primaryRefreshing"
      :secondary-refreshing="false"
      :validators="eth2Validators.entries"
      :filter="selection"
      :rewards="rewards"
      :rewards-loading="rewardsLoading"
      :eth2-details="details"
      :eth2-details-loading="detailsLoading"
      :eth2-stats="dailyStats"
      :eth2-stats-loading="dailyStatsLoading"
      :ownership="ownership"
      @refresh="refresh(true)"
      @update:stats-pagination="pagination = $event"
    >
      <template #selection>
        <v-row>
          <v-col>
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <div v-bind="attrs" v-on="on">
                  <v-btn-toggle v-model="filterType" dense mandatory>
                    <v-btn value="key">{{ t('eth2_page.toggle.key') }}</v-btn>
                    <v-btn value="address">
                      {{ t('eth2_page.toggle.depositor') }}
                    </v-btn>
                  </v-btn-toggle>
                </div>
              </template>
              <span>{{ t('eth2_page.toggle.hint') }}</span>
            </v-tooltip>
          </v-col>
          <v-col cols="12" md="6">
            <eth2-validator-filter
              v-model="selection"
              :filter-type="filterType"
            />
          </v-col>
        </v-row>
      </template>
      <template #modules>
        <active-modules :modules="[module]" />
      </template>
    </eth2-staking>
  </div>
</template>
