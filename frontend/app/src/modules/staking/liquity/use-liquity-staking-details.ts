import type {
  Account,
  LiquityPoolDetailEntry,
  LiquityStakingDetailEntry,
  LiquityStatisticDetails,
} from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import {
  aggregateEntries,
  aggregateStatistics,
  collectAvailableAddresses,
  collectProxies,
} from '@/modules/staking/liquity/liquity-aggregation';
import { useLiquityStore } from '@/modules/staking/liquity/use-liquity-store';
import { ActivityKind, ActivityPart, type ActivitySteps } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseLiquityStakingDetailsReturn {
  accountFilter: ComputedRef<Account[]>;
  aggregatedStake: ComputedRef<LiquityStakingDetailEntry | null>;
  aggregatedStakingPool: ComputedRef<LiquityPoolDetailEntry | null>;
  aggregatedStatistic: ComputedRef<LiquityStatisticDetails | null>;
  availableAddresses: ComputedRef<string[]>;
  liquityHistoricPriceStatus: ReturnType<ReturnType<typeof useHistoricCachePriceStore>['getProtocolStatsPriceQueryStatus']>;
  loading: ComputedRef<boolean>;
  modelSelectedAccounts: Ref<AddressAccount[]>;
  proxyInformation: ComputedRef<Record<string, string[]> | null>;
  stakingQueryStatus: ComputedRef<ActivitySteps | undefined>;
}

export function useLiquityStakingDetails(): UseLiquityStakingDetailsReturn {
  const { staking, stakingPools, statistics } = storeToRefs(useLiquityStore());
  const { useActivity, useIsActive } = useTaskCenter();
  const { getProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();

  const modelSelectedAccounts = ref<AddressAccount[]>([]);

  const stakingActivity = useActivity(ActivityKind.LIQUITY, ActivityPart.STAKE);
  const stakingQueryStatus = computed<ActivitySteps | undefined>(() => get(stakingActivity)?.steps);
  const liquityHistoricPriceStatus = getProtocolStatsPriceQueryStatus('liquity');
  const loading = useIsActive(ActivityKind.LIQUITY, ActivityPart.STAKE);

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
    liquityHistoricPriceStatus,
    loading,
    modelSelectedAccounts,
    proxyInformation,
    stakingQueryStatus,
  };
}
