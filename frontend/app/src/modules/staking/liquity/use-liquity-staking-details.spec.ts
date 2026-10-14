import type { ComputedRef } from 'vue';
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import {
  bigNumberify,
  type LiquityPoolDetails,
  type LiquityStakingDetails,
  type LiquityStatistics,
} from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useLiquityStakingDetails } from './use-liquity-staking-details';

const OWNER_A = '0xaaa';
const OWNER_B = '0xbbb';

interface StoreState {
  pools: LiquityPoolDetails;
  staking: LiquityStakingDetails;
  statistics: LiquityStatistics | null;
}

const { isActive, storeState } = vi.hoisted(() => {
  const storeState: StoreState = { pools: {}, staking: {}, statistics: null };

  return { isActive: { current: false }, storeState };
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
      useIsActive: (): ComputedRef<boolean> => computed(() => isActive.current),
    }),
  };
});

vi.mock('pinia', async importOriginal => ({
  ...(await importOriginal<typeof import('pinia')>()),
  storeToRefs: (store: Record<string, unknown>): Record<string, unknown> => store,
}));

function account(address: string): AddressAccount {
  return createAccount({ address, label: null, tags: null }, 'eth');
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
  function setup(): ReturnType<typeof useLiquityStakingDetails> {
    return withSetup(() => useLiquityStakingDetails()).result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    isActive.current = false;
    storeState.pools = {};
    storeState.staking = {};
    storeState.statistics = null;
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
    storeState.pools = { [OWNER_B]: { balances: null, proxies: null } };

    expect(get(setup().availableAddresses)).toEqual([OWNER_A, OWNER_B]);
  });

  it('should build the history filter from the selected accounts', () => {
    const { accountFilter, modelSelectedAccounts } = setup();
    expect(get(accountFilter)).toEqual([]);

    set(modelSelectedAccounts, [account(OWNER_A)]);

    expect(get(accountFilter)).toEqual([{ address: OWNER_A, chain: 'eth' }]);
  });

  it('should follow the liquity staking activity for its loading state', () => {
    isActive.current = true;

    expect(get(setup().loading)).toBe(true);
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
