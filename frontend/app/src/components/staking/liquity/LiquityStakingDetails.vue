<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type LiquityPoolDetail,
  type LiquityStakingDetail
} from '@rotki/common/lib/liquity';
import { type ComputedRef, type Ref } from 'vue';
import {
  HistoryEventType,
  TransactionEventProtocol
} from '@rotki/common/lib/history/tx-events';
import { Section } from '@/types/status';
import { balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
const liquityStore = useLiquityStore();
const { staking, stakingPools } = toRefs(liquityStore);
const { fetchStaking, fetchPools } = liquityStore;

const { isLoading } = useStatusStore();
const loading = isLoading(Section.DEFI_LIQUITY_STAKING);

const chains = [Blockchain.ETH];

const { tc } = useI18n();

const aggregatedStake: ComputedRef<LiquityStakingDetail | null> = computed(
  () => {
    const allStakes = get(staking);
    let stakes: LiquityStakingDetail | null = null;

    for (const address in allStakes) {
      const account = get(selectedAccounts);
      if (account.length > 0 && account[0].address !== address) {
        continue;
      }
      const stake = allStakes[address];
      if (stakes === null) {
        stakes = { ...stake };
      } else {
        stakes.ethRewards = {
          asset: stakes.ethRewards.asset,
          ...balanceSum(stakes.ethRewards, stake.ethRewards)
        };
        stakes.lusdRewards = {
          asset: stakes.lusdRewards.asset,
          ...balanceSum(stakes.lusdRewards, stake.lusdRewards)
        };
        stakes.staked = {
          asset: stakes.staked.asset,
          ...balanceSum(stakes.staked, stake.staked)
        };
      }
    }
    return stakes;
  }
);

const aggregatedStakingPool: ComputedRef<LiquityPoolDetail | null> = computed(
  () => {
    const allPools = get(stakingPools);
    let pools: LiquityPoolDetail | null = null;

    for (const address in allPools) {
      const account = get(selectedAccounts);
      if (account.length > 0 && account[0].address !== address) {
        continue;
      }
      const pool = allPools[address];
      if (pools === null) {
        pools = { ...pool };
      } else {
        pools.gains = {
          asset: pools.gains.asset,
          ...balanceSum(pools.gains, pool.gains)
        };
        pools.rewards = {
          asset: pools.rewards.asset,
          ...balanceSum(pools.rewards, pool.rewards)
        };
        pools.deposited = {
          asset: pools.deposited.asset,
          ...balanceSum(pools.deposited, pool.deposited)
        };
      }
    }
    return pools;
  }
);

const availableAddresses = computed(() => {
  return [
    ...Object.keys(get(staking)),
    ...Object.keys(get(stakingPools))
  ].filter(uniqueStrings);
});

const refresh = async () => {
  await fetchStaking(true);
  await fetchPools(true);
};
</script>

<template>
  <div>
    <v-row align="center" no-gutters class="pt-2">
      <v-col cols="6">
        <blockchain-account-selector
          v-model="selectedAccounts"
          :label="tc('liquity_staking_details.select_account')"
          :chains="chains"
          dense
          outlined
          no-padding
          flat
          :usable-addresses="availableAddresses"
        />
      </v-col>
      <v-col />
      <v-col v-if="$slots.modules" cols="auto">
        <slot name="modules" />
      </v-col>
      <v-col cols="auto" class="pl-2">
        <refresh-button
          :tooltip="tc('liquity_staking_details.refresh_tooltip')"
          :loading="loading"
          @refresh="refresh"
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col md="6" cols="12">
        <liquity-pools :pool="aggregatedStakingPool" />
      </v-col>

      <v-col md="6" cols="12">
        <liquity-stake :stake="aggregatedStake" />
      </v-col>
    </v-row>

    <transaction-content
      use-external-account-filter
      :section-title="tc('liquity_staking_events.title')"
      :protocols="[TransactionEventProtocol.LIQUITY]"
      :event-types="[HistoryEventType.STAKING]"
      :external-account-filter="selectedAccounts"
    />
  </div>
</template>
