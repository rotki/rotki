import type {
  Account,
  LiquityPoolDetailEntry,
  LiquityStakingDetailEntry,
  LiquityStatisticDetails,
} from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import {
  aggregateEntries,
  aggregateStatistics,
  collectAvailableAddresses,
  collectProxies,
} from '@/modules/staking/liquity/liquity-aggregation';
import { liquityActivity } from '@/modules/staking/liquity/liquity.activity';
import { useLiquityStore } from '@/modules/staking/liquity/use-liquity-store';
import { ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseLiquityStakingDetailsReturn {
  accountFilter: ComputedRef<Account[]>;
  aggregatedStake: ComputedRef<LiquityStakingDetailEntry | null>;
  aggregatedStakingPool: ComputedRef<LiquityPoolDetailEntry | null>;
  aggregatedStatistic: ComputedRef<LiquityStatisticDetails | null>;
  availableAddresses: ComputedRef<string[]>;
  loading: ComputedRef<boolean>;
  modelSelectedAccounts: Ref<AddressAccount[]>;
  proxyInformation: ComputedRef<Record<string, string[]> | null>;
}

export function useLiquityStakingDetails(): UseLiquityStakingDetailsReturn {
  const { staking, stakingPools, statistics } = storeToRefs(useLiquityStore());
  const { useIsActive } = useTaskCenter();

  const modelSelectedAccounts = ref<AddressAccount[]>([]);

  // What is being read, and how far along, is reported in the task dock; the page only needs to know a refresh runs.
  const loading = useIsActive(liquityActivity.kind, ...liquityActivity.partsOf({ part: ActivityPart.STAKE }));

  const selectedAddresses = computed<string[]>(() =>
    get(modelSelectedAccounts).map(({ address }) => address));

  const accountFilter = computed<Account[]>(() =>
    get(modelSelectedAccounts).map(({ address, chain }) => ({ address, chain })));

  const aggregatedStake = computed<LiquityStakingDetailEntry | null>(() =>
    aggregateEntries(get(staking), get(selectedAddresses)));

  const aggregatedStakingPool = computed<LiquityPoolDetailEntry | null>(() =>
    aggregateEntries(get(stakingPools), get(selectedAddresses)));

  const proxyInformation = computed<Record<string, string[]> | null>(() =>
    collectProxies(get(staking), get(stakingPools), get(selectedAddresses)));

  const aggregatedStatistic = computed<LiquityStatisticDetails | null>(() =>
    aggregateStatistics(get(statistics), get(selectedAddresses)));

  const availableAddresses = computed<string[]>(() =>
    collectAvailableAddresses(get(staking), get(stakingPools)));

  return {
    accountFilter,
    aggregatedStake,
    aggregatedStakingPool,
    aggregatedStatistic,
    availableAddresses,
    loading,
    modelSelectedAccounts,
    proxyInformation,
  };
}
