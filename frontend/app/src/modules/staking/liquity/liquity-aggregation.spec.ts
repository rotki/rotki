import {
  type AssetBalance,
  bigNumberify,
  type LiquityPoolDetails,
  type LiquityStakingDetailEntry,
  type LiquityStakingDetails,
  type LiquityStatisticDetails,
  type LiquityStatistics,
} from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  aggregateEntries,
  aggregateStatistics,
  collectAvailableAddresses,
  collectProxies,
  mergeAssetBalances,
} from './liquity-aggregation';

const OWNER_A = '0xaaa';
const OWNER_B = '0xbbb';
const PROXY_A = '0xproxy-a';
const PROXY_B = '0xproxy-b';

function assetBalance(asset: string, amount: number, value = amount * 2): AssetBalance {
  return { amount: bigNumberify(amount), asset, value: bigNumberify(value) };
}

function stake(staked: number, ethRewards = 0, lusdRewards = 0): LiquityStakingDetailEntry {
  return {
    ethRewards: assetBalance('ETH', ethRewards),
    lusdRewards: assetBalance('LUSD', lusdRewards),
    staked: assetBalance('LQTY', staked),
  };
}

function statistic(overrides: Partial<LiquityStatisticDetails> = {}): LiquityStatisticDetails {
  return {
    stabilityPoolGains: [],
    stakingGains: [],
    totalDepositedStabilityPool: bigNumberify(0),
    totalDepositedStabilityPoolValue: bigNumberify(0),
    totalValueGainsStabilityPool: bigNumberify(0),
    totalValueGainsStaking: bigNumberify(0),
    totalWithdrawnStabilityPool: bigNumberify(0),
    totalWithdrawnStabilityPoolValue: bigNumberify(0),
    ...overrides,
  };
}

describe('modules/staking/liquity/aggregateEntries', () => {
  it('should be null when there is nothing at all', () => {
    expect(aggregateEntries({}, [])).toBeNull();
  });

  it('should be null when the owner holds neither a balance nor a proxy', () => {
    const source: LiquityStakingDetails = { [OWNER_A]: { balances: null, proxies: null } };

    expect(aggregateEntries(source, [])).toBeNull();
  });

  it('should return the single owned balance untouched', () => {
    const source: LiquityStakingDetails = { [OWNER_A]: { balances: stake(100), proxies: null } };

    const total = aggregateEntries(source, []);

    expect(total?.staked.amount.toNumber()).toBe(100);
    expect(total?.staked.asset).toBe('LQTY');
  });

  it('should sum every field across owners', () => {
    const source: LiquityStakingDetails = {
      [OWNER_A]: { balances: stake(100, 1, 10), proxies: null },
      [OWNER_B]: { balances: stake(50, 2, 20), proxies: null },
    };

    const total = aggregateEntries(source, []);

    expect(total?.staked.amount.toNumber()).toBe(150);
    expect(total?.ethRewards.amount.toNumber()).toBe(3);
    expect(total?.lusdRewards.amount.toNumber()).toBe(30);
  });

  it('should sum the value alongside the amount', () => {
    const source: LiquityStakingDetails = {
      [OWNER_A]: { balances: stake(100), proxies: null },
      [OWNER_B]: { balances: stake(50), proxies: null },
    };

    expect(aggregateEntries(source, [])?.staked.value.toNumber()).toBe(300);
  });

  it('should keep the asset identifier while summing', () => {
    const source: LiquityStakingDetails = {
      [OWNER_A]: { balances: stake(100), proxies: null },
      [OWNER_B]: { balances: stake(50), proxies: null },
    };

    expect(aggregateEntries(source, [])?.staked.asset).toBe('LQTY');
  });

  it('should include balances held through a proxy', () => {
    const source: LiquityStakingDetails = {
      [OWNER_A]: { balances: stake(100), proxies: { [PROXY_A]: stake(25), [PROXY_B]: stake(25) } },
    };

    expect(aggregateEntries(source, [])?.staked.amount.toNumber()).toBe(150);
  });

  it('should include a proxy balance when the owner has none of their own', () => {
    const source: LiquityStakingDetails = {
      [OWNER_A]: { balances: null, proxies: { [PROXY_A]: stake(25) } },
    };

    expect(aggregateEntries(source, [])?.staked.amount.toNumber()).toBe(25);
  });

  describe('the account filter', () => {
    const source: LiquityStakingDetails = {
      [OWNER_A]: { balances: stake(100), proxies: null },
      [OWNER_B]: { balances: stake(50), proxies: null },
    };

    it('should treat an empty selection as every address', () => {
      expect(aggregateEntries(source, [])?.staked.amount.toNumber()).toBe(150);
    });

    it('should keep only the selected address', () => {
      expect(aggregateEntries(source, [OWNER_B])?.staked.amount.toNumber()).toBe(50);
    });

    it('should be null when the selection matches no address', () => {
      expect(aggregateEntries(source, ['0xnobody'])).toBeNull();
    });
  });

  it('should not mutate the source entries', () => {
    const owned = stake(100);
    const source: LiquityStakingDetails = {
      [OWNER_A]: { balances: owned, proxies: null },
      [OWNER_B]: { balances: stake(50), proxies: null },
    };

    aggregateEntries(source, []);

    expect(owned.staked.amount.toNumber()).toBe(100);
  });

  it('should serve pool details, which have the same shape', () => {
    const pools: LiquityPoolDetails = {
      [OWNER_A]: {
        balances: {
          deposited: assetBalance('LUSD', 500),
          gains: assetBalance('ETH', 1),
          rewards: assetBalance('LQTY', 5),
        },
        proxies: null,
      },
    };

    expect(aggregateEntries(pools, [])?.deposited.amount.toNumber()).toBe(500);
  });
});

describe('modules/staking/liquity/collectProxies', () => {
  const staking: LiquityStakingDetails = {
    [OWNER_A]: { balances: null, proxies: { [PROXY_A]: stake(1) } },
  };
  const pools: LiquityPoolDetails = {};

  it('should be null when no address was selected', () => {
    // With no account filter there is no owner to attribute a proxy to.
    expect(collectProxies(staking, pools, [])).toBeNull();
  });

  it('should be null when the selected address holds no proxy', () => {
    expect(collectProxies(staking, pools, [OWNER_B])).toBeNull();
  });

  it('should list the proxies of a selected address', () => {
    expect(collectProxies(staking, pools, [OWNER_A])).toEqual({ [OWNER_A]: [PROXY_A] });
  });

  it('should combine the staking and pool proxies of one address', () => {
    const withPool: LiquityPoolDetails = {
      [OWNER_A]: { balances: null, proxies: { [PROXY_B]: { deposited: assetBalance('LUSD', 1), gains: assetBalance('ETH', 0), rewards: assetBalance('LQTY', 0) } } },
    };

    expect(collectProxies(staking, withPool, [OWNER_A])).toEqual({ [OWNER_A]: [PROXY_B, PROXY_A] });
  });

  it('should list a proxy once when it serves both staking and a pool', () => {
    const samePool: LiquityPoolDetails = {
      [OWNER_A]: { balances: null, proxies: { [PROXY_A]: { deposited: assetBalance('LUSD', 1), gains: assetBalance('ETH', 0), rewards: assetBalance('LQTY', 0) } } },
    };

    expect(collectProxies(staking, samePool, [OWNER_A])).toEqual({ [OWNER_A]: [PROXY_A] });
  });

  it('should key the proxies by their owner', () => {
    const twoOwners: LiquityStakingDetails = {
      [OWNER_A]: { balances: null, proxies: { [PROXY_A]: stake(1) } },
      [OWNER_B]: { balances: null, proxies: { [PROXY_B]: stake(1) } },
    };

    expect(collectProxies(twoOwners, pools, [OWNER_A, OWNER_B])).toEqual({
      [OWNER_A]: [PROXY_A],
      [OWNER_B]: [PROXY_B],
    });
  });
});

describe('modules/staking/liquity/mergeAssetBalances', () => {
  it('should sum two entries naming the same asset', () => {
    const merged = mergeAssetBalances([assetBalance('ETH', 1)], [assetBalance('ETH', 2)]);

    expect(merged).toHaveLength(1);
    expect(merged[0].amount.toNumber()).toBe(3);
    expect(merged[0].value.toNumber()).toBe(6);
  });

  it('should keep entries for different assets apart', () => {
    const merged = mergeAssetBalances([assetBalance('ETH', 1)], [assetBalance('LUSD', 2)]);

    expect(merged.map(item => item.asset)).toEqual(['ETH', 'LUSD']);
  });

  it('should carry a list through when the other is empty', () => {
    expect(mergeAssetBalances([assetBalance('ETH', 1)], [])[0].amount.toNumber()).toBe(1);
    expect(mergeAssetBalances([], [assetBalance('ETH', 1)])[0].amount.toNumber()).toBe(1);
  });

  it('should be empty when both are', () => {
    expect(mergeAssetBalances([], [])).toEqual([]);
  });
});

describe('modules/staking/liquity/aggregateStatistics', () => {
  it('should be null without statistics', () => {
    expect(aggregateStatistics(null, [])).toBeNull();
  });

  describe('with no address selected', () => {
    it('should use the global figure the backend aggregated', () => {
      const statistics: LiquityStatistics = {
        globalStats: statistic({ totalValueGainsStaking: bigNumberify(99) }),
      };

      expect(aggregateStatistics(statistics, [])?.totalValueGainsStaking.toNumber()).toBe(99);
    });

    it('should be null when there is no global figure', () => {
      expect(aggregateStatistics({ byAddress: {} }, [])).toBeNull();
    });

    it('should not fall back to the per-address figures', () => {
      const statistics: LiquityStatistics = {
        byAddress: { [OWNER_A]: statistic({ totalValueGainsStaking: bigNumberify(5) }) },
      };

      expect(aggregateStatistics(statistics, [])).toBeNull();
    });
  });

  describe('with addresses selected', () => {
    const statistics: LiquityStatistics = {
      byAddress: {
        [OWNER_A]: statistic({
          stakingGains: [assetBalance('ETH', 1)],
          totalValueGainsStaking: bigNumberify(10),
        }),
        [OWNER_B]: statistic({
          stakingGains: [assetBalance('ETH', 2), assetBalance('LUSD', 7)],
          totalValueGainsStaking: bigNumberify(20),
        }),
      },
      globalStats: statistic({ totalValueGainsStaking: bigNumberify(999) }),
    };

    it('should use the selected address rather than the global figure', () => {
      expect(aggregateStatistics(statistics, [OWNER_A])?.totalValueGainsStaking.toNumber()).toBe(10);
    });

    it('should sum the numeric totals across selected addresses', () => {
      expect(aggregateStatistics(statistics, [OWNER_A, OWNER_B])?.totalValueGainsStaking.toNumber()).toBe(30);
    });

    it('should merge the gain lists per asset', () => {
      const total = aggregateStatistics(statistics, [OWNER_A, OWNER_B]);

      const eth = total?.stakingGains.find(item => item.asset === 'ETH');
      expect(eth?.amount.toNumber()).toBe(3);
      expect(total?.stakingGains.find(item => item.asset === 'LUSD')?.amount.toNumber()).toBe(7);
    });

    it('should be null when no statistics are broken down by address', () => {
      expect(aggregateStatistics({ globalStats: statistic() }, [OWNER_A])).toBeNull();
    });

    it('should be null when the selection matches no address with statistics', () => {
      expect(aggregateStatistics(statistics, ['0xnobody'])).toBeNull();
    });

    it('should not mutate the source statistics', () => {
      aggregateStatistics(statistics, [OWNER_A, OWNER_B]);

      expect(statistics.byAddress?.[OWNER_A].totalValueGainsStaking.toNumber()).toBe(10);
      expect(statistics.byAddress?.[OWNER_A].stakingGains).toHaveLength(1);
    });
  });
});

describe('modules/staking/liquity/collectAvailableAddresses', () => {
  it('should list an address that only stakes', () => {
    const staking: LiquityStakingDetails = { [OWNER_A]: { balances: stake(1), proxies: null } };

    expect(collectAvailableAddresses(staking, {})).toEqual([OWNER_A]);
  });

  it('should list an address that only pools', () => {
    const pools: LiquityPoolDetails = {
      [OWNER_B]: { balances: { deposited: assetBalance('LUSD', 1), gains: assetBalance('ETH', 0), rewards: assetBalance('LQTY', 0) }, proxies: null },
    };

    expect(collectAvailableAddresses({}, pools)).toEqual([OWNER_B]);
  });

  it('should list an address doing both only once', () => {
    const staking: LiquityStakingDetails = { [OWNER_A]: { balances: stake(1), proxies: null } };
    const pools: LiquityPoolDetails = {
      [OWNER_A]: { balances: { deposited: assetBalance('LUSD', 1), gains: assetBalance('ETH', 0), rewards: assetBalance('LQTY', 0) }, proxies: null },
    };

    expect(collectAvailableAddresses(staking, pools)).toEqual([OWNER_A]);
  });

  it('should be empty with nothing at all', () => {
    expect(collectAvailableAddresses({}, {})).toEqual([]);
  });
});
