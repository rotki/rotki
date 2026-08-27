import {
  type AssetBalance,
  bigNumberify,
  type LiquityPoolDetailEntry,
  type LiquityStatisticDetails,
  One,
} from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  calculatePnl,
  orOne,
  type PriceLookup,
  priceOrOne,
  repriceStatistic,
  StatisticView,
} from './liquity-statistics';

function assetBalance(asset: string, amount: number, value = amount): AssetBalance {
  return { amount: bigNumberify(amount), asset, value: bigNumberify(value) };
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

function pool(overrides: Partial<LiquityPoolDetailEntry> = {}): LiquityPoolDetailEntry {
  return {
    deposited: assetBalance('LUSD', 0),
    gains: assetBalance('ETH', 0),
    rewards: assetBalance('LQTY', 0),
    ...overrides,
  };
}

/** Prices every asset it knows; anything else has no price at all. */
function pricesOf(prices: Record<string, number>): PriceLookup {
  return (asset: string) => asset in prices ? bigNumberify(prices[asset]) : undefined;
}

describe('modules/staking/liquity/orOne', () => {
  it('should use a real price', () => {
    expect(orOne(bigNumberify(5)).toNumber()).toBe(5);
  });

  it('should fall back to one when there is no price', () => {
    expect(orOne(undefined)).toStrictEqual(One);
  });

  it('should fall back to one for a zero price, which would collapse the row', () => {
    expect(orOne(bigNumberify(0))).toStrictEqual(One);
  });
});

describe('modules/staking/liquity/priceOrOne', () => {
  it('should look the asset price up', () => {
    expect(priceOrOne(pricesOf({ ETH: 3000 }), 'ETH').toNumber()).toBe(3000);
  });

  it('should fall back to one for an unpriced asset', () => {
    expect(priceOrOne(pricesOf({}), 'ETH')).toStrictEqual(One);
  });
});

describe('modules/staking/liquity/repriceStatistic', () => {
  const recorded = statistic({
    stabilityPoolGains: [assetBalance('ETH', 2, 100)],
    stakingGains: [assetBalance('LQTY', 10, 20)],
    totalDepositedStabilityPool: bigNumberify(1000),
    totalDepositedStabilityPoolValue: bigNumberify(1000),
    totalValueGainsStabilityPool: bigNumberify(100),
    totalValueGainsStaking: bigNumberify(20),
    totalWithdrawnStabilityPool: bigNumberify(400),
    totalWithdrawnStabilityPoolValue: bigNumberify(400),
  });

  it('should return the recorded figures untouched on the historical view', () => {
    const priced = repriceStatistic(recorded, StatisticView.HISTORICAL, pricesOf({ ETH: 3000 }), bigNumberify(2));

    expect(priced).toBe(recorded);
  });

  describe('on the current view', () => {
    const priceOf = pricesOf({ ETH: 3000, LQTY: 5 });

    it('should re-value each gain at its current price', () => {
      const priced = repriceStatistic(recorded, StatisticView.CURRENT, priceOf, One);

      expect(priced.stabilityPoolGains[0].value.toNumber()).toBe(6000);
      expect(priced.stakingGains[0].value.toNumber()).toBe(50);
    });

    it('should keep the amounts as they were', () => {
      const priced = repriceStatistic(recorded, StatisticView.CURRENT, priceOf, One);

      expect(priced.stabilityPoolGains[0].amount.toNumber()).toBe(2);
    });

    it('should total the re-valued gains', () => {
      const priced = repriceStatistic(recorded, StatisticView.CURRENT, priceOf, One);

      expect(priced.totalValueGainsStabilityPool.toNumber()).toBe(6000);
      expect(priced.totalValueGainsStaking.toNumber()).toBe(50);
    });

    it('should re-value the LUSD totals at the LUSD price', () => {
      const priced = repriceStatistic(recorded, StatisticView.CURRENT, priceOf, bigNumberify(2));

      expect(priced.totalDepositedStabilityPoolValue.toNumber()).toBe(2000);
      expect(priced.totalWithdrawnStabilityPoolValue.toNumber()).toBe(800);
    });

    it('should leave an unpriced gain at its amount, not at zero, an unknown price being no claim of worthlessness', () => {
      const priced = repriceStatistic(recorded, StatisticView.CURRENT, pricesOf({}), One);

      expect(priced.stabilityPoolGains[0].value.toNumber()).toBe(2);
      expect(priced.totalValueGainsStabilityPool.toNumber()).toBe(2);
    });

    it('should value a gain priced explicitly at zero as zero', () => {
      const priced = repriceStatistic(recorded, StatisticView.CURRENT, pricesOf({ ETH: 0 }), One);

      expect(priced.stabilityPoolGains[0].value.toNumber()).toBe(0);
    });

    it('should not mutate the recorded statistic', () => {
      repriceStatistic(recorded, StatisticView.CURRENT, priceOf, bigNumberify(2));

      expect(recorded.stabilityPoolGains[0].value.toNumber()).toBe(100);
      expect(recorded.totalDepositedStabilityPoolValue.toNumber()).toBe(1000);
    });

    it('should total an empty gain list as zero', () => {
      const priced = repriceStatistic(statistic(), StatisticView.CURRENT, priceOf, One);

      expect(priced.totalValueGainsStaking.toNumber()).toBe(0);
    });
  });
});

describe('modules/staking/liquity/calculatePnl', () => {
  const DEPOSITED = 1000;
  const WITHDRAWN = 400;
  const GAINS = 50;
  const OWED_BY_THE_POOL = DEPOSITED - WITHDRAWN;

  const depositHistory = (): ReturnType<typeof statistic> => statistic({
    totalDepositedStabilityPool: bigNumberify(DEPOSITED),
    totalValueGainsStabilityPool: bigNumberify(GAINS),
    totalWithdrawnStabilityPool: bigNumberify(WITHDRAWN),
  });

  it('should be the gains when nothing was consumed by a liquidation', () => {
    const result = calculatePnl(
      depositHistory(),
      pool({ deposited: assetBalance('LUSD', OWED_BY_THE_POOL) }),
      pricesOf({}),
      One,
    );

    expect(result.toNumber()).toBe(GAINS);
  });

  it('should subtract the LUSD a liquidation consumed', () => {
    const consumedByLiquidation = 100;
    const result = calculatePnl(
      depositHistory(),
      pool({ deposited: assetBalance('LUSD', OWED_BY_THE_POOL - consumedByLiquidation) }),
      pricesOf({}),
      One,
    );

    expect(result.toNumber()).toBe(GAINS - consumedByLiquidation);
  });

  it('should price the consumed LUSD at the given LUSD price', () => {
    const result = calculatePnl(
      statistic({
        totalDepositedStabilityPool: bigNumberify(1000),
        totalValueGainsStabilityPool: bigNumberify(50),
        totalWithdrawnStabilityPool: bigNumberify(400),
      }),
      pool({ deposited: assetBalance('LUSD', 500) }),
      pricesOf({}),
      bigNumberify(2),
    );

    expect(result.toNumber()).toBe(-150);
  });

  it('should add the liquidation gains at their current price', () => {
    const result = calculatePnl(
      statistic({ totalDepositedStabilityPool: bigNumberify(0) }),
      pool({ gains: assetBalance('ETH', 2) }),
      pricesOf({ ETH: 3000 }),
      One,
    );

    expect(result.toNumber()).toBe(6000);
  });

  it('should add the rewards at their current price', () => {
    const result = calculatePnl(
      statistic({ totalDepositedStabilityPool: bigNumberify(0) }),
      pool({ rewards: assetBalance('LQTY', 10) }),
      pricesOf({ LQTY: 5 }),
      One,
    );

    expect(result.toNumber()).toBe(50);
  });

  it('should count an unpriced gain at its face amount rather than dropping it', () => {
    const result = calculatePnl(
      statistic({ totalDepositedStabilityPool: bigNumberify(0) }),
      pool({ gains: assetBalance('ETH', 2) }),
      pricesOf({}),
      One,
    );

    expect(result.toNumber()).toBe(2);
  });

  it('should combine every part', () => {
    const result = calculatePnl(
      statistic({
        totalDepositedStabilityPool: bigNumberify(1000),
        totalValueGainsStabilityPool: bigNumberify(50),
        totalWithdrawnStabilityPool: bigNumberify(400),
      }),
      pool({
        deposited: assetBalance('LUSD', 500),
        gains: assetBalance('ETH', 1),
        rewards: assetBalance('LQTY', 10),
      }),
      pricesOf({ ETH: 3000, LQTY: 5 }),
      One,
    );

    // gains 50 + eth 3000 + lqty 50, less the 100 LUSD consumed
    expect(result.toNumber()).toBe(3000);
  });
});
