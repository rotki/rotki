import type { VueWrapper } from '@vue/test-utils';
import type { ComputedRef } from 'vue';
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { StatsPriceQueryData } from '@/modules/core/messaging/types';
import type { ActivitySteps } from '@/modules/task-center/core/types';
import {
  bigNumberify,
  type LiquityPoolDetails,
  type LiquityStakingDetails,
  type LiquityStatistics,
} from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { withSetup } from '@test/utils/with-setup';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLiquityStakingDetails } from './use-liquity-staking-details';

const OWNER_A = '0xaaa';
const OWNER_B = '0xbbb';

interface StoreState {
  pools: LiquityPoolDetails;
  staking: LiquityStakingDetails;
  statistics: LiquityStatistics | null;
}

const { activity, isActive, priceStatus, storeState } = vi.hoisted(() => {
  const activity: { current?: { steps?: ActivitySteps } } = {};
  const priceStatus: { current?: StatsPriceQueryData } = {};
  const storeState: StoreState = { pools: {}, staking: {}, statistics: null };

  return { activity, isActive: { current: false }, priceStatus, storeState };
});

vi.mock('@/modules/staking/liquity/use-liquity-store', async () => {
  const { computed } = await import('vue');
  return {
    useLiquityStore: (): Record<string, unknown> => ({
      staking: computed(() => storeState.staking),
      stakingPools: computed(() => storeState.pools),
      statistics: computed(() => storeState.statistics),
    }),
  };
});

vi.mock('@/modules/task-center/use-task-center', async () => {
  const { computed } = await import('vue');
  return {
    useTaskCenter: (): Record<string, unknown> => ({
      useActivity: (): ComputedRef<unknown> => computed(() => activity.current),
      useIsActive: (): ComputedRef<boolean> => computed(() => isActive.current),
    }),
  };
});

vi.mock('@/modules/assets/prices/use-historic-cache-price-store', async () => {
  const { computed } = await import('vue');
  return {
    useHistoricCachePriceStore: (): Record<string, unknown> => ({
      getProtocolStatsPriceQueryStatus: (): ComputedRef<unknown> => computed(() => priceStatus.current),
    }),
  };
});

vi.mock('pinia', async importOriginal => ({
  ...(await importOriginal<typeof import('pinia')>()),
  storeToRefs: (store: Record<string, unknown>): Record<string, unknown> => store,
}));

function account(address: string): BlockchainAccount<AddressData> {
  return createMock<BlockchainAccount<AddressData>>({
    chain: 'eth',
    data: { address, type: 'address' },
  });
}

function stakeOf(amount: number): LiquityStakingDetails[string] {
  const balance = (asset: string, value: number): { amount: ReturnType<typeof bigNumberify>; asset: string; value: ReturnType<typeof bigNumberify> } => ({
    amount: bigNumberify(value),
    asset,
    value: bigNumberify(value),
  });

  return {
    balances: {
      ethRewards: balance('ETH', 0),
      lusdRewards: balance('LUSD', 0),
      staked: balance('LQTY', amount),
    },
    proxies: null,
  };
}

describe('modules/staking/liquity/useLiquityStakingDetails', () => {
  const mounted: VueWrapper[] = [];

  function setup(): ReturnType<typeof useLiquityStakingDetails> {
    const { result, wrapper } = withSetup(() => useLiquityStakingDetails());
    mounted.push(wrapper);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    activity.current = undefined;
    isActive.current = false;
    priceStatus.current = undefined;
    storeState.pools = {};
    storeState.staking = {};
    storeState.statistics = null;
  });

  afterEach(() => {
    while (mounted.length > 0)
      mounted.pop()?.unmount();
  });

  it('should start with nothing selected, so every address is aggregated', () => {
    storeState.staking = { [OWNER_A]: stakeOf(100), [OWNER_B]: stakeOf(50) };

    const { aggregatedStake, modelSelectedAccounts } = setup();

    expect(get(modelSelectedAccounts)).toEqual([]);
    expect(get(aggregatedStake)?.staked.amount.toNumber()).toBe(150);
  });

  it('should narrow the aggregate to the selected account', () => {
    storeState.staking = { [OWNER_A]: stakeOf(100), [OWNER_B]: stakeOf(50) };

    const { aggregatedStake, modelSelectedAccounts } = setup();
    set(modelSelectedAccounts, [account(OWNER_B)]);

    expect(get(aggregatedStake)?.staked.amount.toNumber()).toBe(50);
  });

  it('should offer every address holding a position, staked or pooled', () => {
    storeState.staking = { [OWNER_A]: stakeOf(100) };
    // A plain literal, not `createMock`: the proxy answers every property, so `Object.keys` on it
    // returns the mock's own method names rather than the addresses.
    storeState.pools = { [OWNER_B]: { balances: null, proxies: null } };

    expect(get(setup().availableAddresses)).toEqual([OWNER_A, OWNER_B]);
  });

  it('should build the history filter from the selected accounts', () => {
    const { accountFilter, modelSelectedAccounts } = setup();
    expect(get(accountFilter)).toEqual([]);

    set(modelSelectedAccounts, [account(OWNER_A)]);

    expect(get(accountFilter)).toEqual([{ address: OWNER_A, chain: 'eth' }]);
  });

  it('should report the staking activity progress', () => {
    activity.current = { steps: { current: 3, total: 10 } };

    expect(get(setup().stakingQueryStatus)).toEqual({ current: 3, total: 10 });
  });

  it('should report no progress when there is no activity', () => {
    expect(get(setup().stakingQueryStatus)).toBeUndefined();
  });

  it('should follow the liquity staking activity for its loading state', () => {
    isActive.current = true;

    expect(get(setup().loading)).toBe(true);
  });

  it('should expose the historic price query status', () => {
    priceStatus.current = { counterparty: 'liquity', processed: 2, total: 5 };

    expect(get(setup().liquityHistoricPriceStatus)).toEqual({ counterparty: 'liquity', processed: 2, total: 5 });
  });

  it('should show the global statistics until an account is chosen', () => {
    storeState.statistics = createMock<LiquityStatistics>({
      byAddress: undefined,
      globalStats: createMock<LiquityStatistics['globalStats']>({
        totalValueGainsStaking: bigNumberify(42),
      }),
    });

    const { aggregatedStatistic, modelSelectedAccounts } = setup();
    expect(get(aggregatedStatistic)?.totalValueGainsStaking.toNumber()).toBe(42);

    // With an account chosen and no per-address breakdown there is nothing to show.
    set(modelSelectedAccounts, [account(OWNER_A)]);
    expect(get(aggregatedStatistic)).toBeNull();
  });

  it('should surface no proxies until an account is chosen', () => {
    storeState.staking = {
      [OWNER_A]: { ...stakeOf(100), proxies: { '0xproxy': stakeOf(1).balances! } },
    };

    const { modelSelectedAccounts, proxyInformation } = setup();
    expect(get(proxyInformation)).toBeNull();

    set(modelSelectedAccounts, [account(OWNER_A)]);

    expect(get(proxyInformation)).toEqual({ [OWNER_A]: ['0xproxy'] });
  });
});
