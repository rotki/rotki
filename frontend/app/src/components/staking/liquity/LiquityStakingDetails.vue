<template>
  <div>
    <v-row align="center" no-gutters class="pt-2">
      <v-col cols="6">
        <blockchain-account-selector
          v-model="selectedAccount"
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
        <liquity-pools :pool="stakingPoolsList" />
      </v-col>

      <v-col md="6" cols="12">
        <liquity-stake :stakings="stakingList" />
      </v-col>
    </v-row>

    <transaction-content
      :section-title="tc('liquity_staking_events.title')"
      :protocol="TransactionEventProtocol.LIQUITY"
      :event-type="HistoryEventType.STAKING"
      :use-external-account-filter="true"
      :external-account-filter="selectedAccount"
      @fetch="fetchTransactions"
    />
  </div>
</template>

<script setup lang="ts">
import { type AssetBalance } from '@rotki/common';
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type LiquityPoolDetail,
  type LiquityPoolDetails,
  type LiquityStaking
} from '@rotki/common/lib/liquity';
import { type ComputedRef } from 'vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TransactionContent from '@/components/history/transactions/TransactionContent.vue';
import LiquityPools from '@/components/staking/liquity/LiquityPools.vue';
import LiquityStake from '@/components/staking/liquity/LiquityStake.vue';
import { isSectionLoading } from '@/composables/common';
import { useLiquityStore } from '@/store/defi/liquity';
import { useTransactions } from '@/store/history/transactions';
import { Section } from '@/types/status';
import {
  HistoryEventType,
  TransactionEventProtocol
} from '@/types/transaction';
import { balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';

const selectedAccount = ref<GeneralAccount | null>(null);
const liquityStore = useLiquityStore();
const { staking, stakingPools } = toRefs(liquityStore);
const { fetchStaking, fetchPools } = liquityStore;

const loading = isSectionLoading(Section.DEFI_LIQUITY_STAKING);
const chains = [Blockchain.ETH];

const { tc } = useI18n();

const stakingList: ComputedRef<AssetBalance[]> = computed(() => {
  const staked: Record<string, AssetBalance> = {};
  const stake = get(staking) as LiquityStaking;

  for (const address in stake) {
    const account = get(selectedAccount);
    if (account && account.address !== address) {
      continue;
    }
    const addressStake = stake[address];
    const asset = addressStake.asset;
    const assetStake = staked[asset];

    if (assetStake) {
      staked[asset] = {
        asset,
        usdValue: assetStake.usdValue.plus(addressStake.usdValue),
        amount: assetStake.amount.plus(addressStake.amount)
      };
    } else {
      staked[asset] = addressStake;
    }
  }
  return Object.values(staked);
});

const stakingPoolsList: ComputedRef<LiquityPoolDetail | null> = computed(() => {
  const allPools = get(stakingPools) as LiquityPoolDetails;
  let pools: LiquityPoolDetail | null = null;

  for (const address in allPools) {
    const account = get(selectedAccount);
    if (account && account.address !== address) {
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
});

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

const { fetchTransactions } = useTransactions();
</script>
