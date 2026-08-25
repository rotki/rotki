import type { VueWrapper } from '@vue/test-utils';
import type { ComputedRef } from 'vue';
import {
  type BigNumber,
  bigNumberify,
  type LiquityPoolDetailEntry,
  type LiquityStatisticDetails,
} from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LUSD_ID } from './liquity-assets';
import { StatisticView } from './liquity-statistics';
import { useLiquityStatistics } from './use-liquity-statistics';

const { isActive, prices } = vi.hoisted(() => {
  const prices: { current: Record<string, number> } = { current: {} };
  return { isActive: { current: false }, prices };
});

vi.mock('@/modules/assets/prices/use-price-utils', async () => {
  const { computed } = await import('vue');
  const { bigNumberify: toBigNumber } = await import('@rotki/common');
  const priceOf = (asset: string): BigNumber | undefined =>
    asset in prices.current ? toBigNumber(prices.current[asset]) : undefined;

  return {
    usePriceUtils: (): Record<string, unknown> => ({
      getAssetPrice: priceOf,
      useAssetPrice: (asset: string): ComputedRef<BigNumber | undefined> => computed(() => priceOf(asset)),
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

function assetBalance(asset: string, amount: number, value = amount): { amount: BigNumber; asset: string; value: BigNumber } {
  return { amount: bigNumberify(amount), asset, value: bigNumberify(value) };
}

function statistic(overrides: Partial<LiquityStatisticDetails> = {}): LiquityStatisticDetails {
  return {
    stabilityPoolGains: [],
    stakingGains: [],
    totalDepositedStabilityPool: bigNumberify(1000),
    totalDepositedStabilityPoolValue: bigNumberify(1000),
    totalValueGainsStabilityPool: bigNumberify(0),
    totalValueGainsStaking: bigNumberify(0),
    totalWithdrawnStabilityPool: bigNumberify(400),
    totalWithdrawnStabilityPoolValue: bigNumberify(400),
    ...overrides,
  };
}

describe('modules/staking/liquity/useLiquityStatistics', () => {
  const mounted: VueWrapper[] = [];

  function setup(
    statisticValue: LiquityStatisticDetails | null,
    poolValue: LiquityPoolDetailEntry | null = null,
  ): ReturnType<typeof useLiquityStatistics> {
    const { result, wrapper } = withSetup(() => useLiquityStatistics({
      pool: () => poolValue,
      statistic: () => statisticValue,
    }));
    mounted.push(wrapper);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    isActive.current = false;
    prices.current = {};
  });

  afterEach(() => {
    while (mounted.length > 0)
      mounted.pop()?.unmount();
  });

  it('should start on the historical view', () => {
    expect(get(setup(statistic()).modelSelection)).toBe(StatisticView.HISTORICAL);
  });

  it('should be null throughout when there are no statistics', () => {
    const { statisticWithAdjustedPrice, totalDepositedStabilityPoolBalance, totalWithdrawnStabilityPoolBalance } = setup(null);

    expect(get(statisticWithAdjustedPrice)).toBeNull();
    expect(get(totalDepositedStabilityPoolBalance)).toBeNull();
    expect(get(totalWithdrawnStabilityPoolBalance)).toBeNull();
  });

  it('should re-value on switching to the current view', () => {
    prices.current = { ETH: 3000 };
    const { modelSelection, statisticWithAdjustedPrice } = setup(statistic({
      stabilityPoolGains: [assetBalance('ETH', 2, 100)],
    }));

    expect(get(statisticWithAdjustedPrice)?.stabilityPoolGains[0].value.toNumber()).toBe(100);

    set(modelSelection, StatisticView.CURRENT);

    expect(get(statisticWithAdjustedPrice)?.stabilityPoolGains[0].value.toNumber()).toBe(6000);
  });

  it('should price the LUSD totals with the LUSD price on the current view', () => {
    prices.current = { [LUSD_ID]: 2 };
    const { modelSelection, totalDepositedStabilityPoolBalance } = setup(statistic());

    set(modelSelection, StatisticView.CURRENT);

    expect(get(totalDepositedStabilityPoolBalance)?.value.toNumber()).toBe(2000);
  });

  it('should fall back to a LUSD price of one when there is none', () => {
    const { modelSelection, totalDepositedStabilityPoolBalance } = setup(statistic());

    set(modelSelection, StatisticView.CURRENT);

    expect(get(totalDepositedStabilityPoolBalance)?.value.toNumber()).toBe(1000);
  });

  it('should pair each total with its own amount', () => {
    const { totalDepositedStabilityPoolBalance, totalWithdrawnStabilityPoolBalance } = setup(statistic());

    expect(get(totalDepositedStabilityPoolBalance)?.amount.toNumber()).toBe(1000);
    expect(get(totalWithdrawnStabilityPoolBalance)?.amount.toNumber()).toBe(400);
  });

  describe('the profit and loss', () => {
    it('should be null without a pool, which is what it is measured against', () => {
      expect(get(setup(statistic()).totalPnl)).toBeNull();
    });

    it('should be null without statistics', () => {
      expect(get(setup(null, { deposited: assetBalance('LUSD', 600), gains: assetBalance('ETH', 0), rewards: assetBalance('LQTY', 0) }).totalPnl)).toBeNull();
    });

    it('should be computed once both are present', () => {
      const { totalPnl } = setup(
        statistic({ totalValueGainsStabilityPool: bigNumberify(50) }),
        { deposited: assetBalance('LUSD', 600), gains: assetBalance('ETH', 0), rewards: assetBalance('LQTY', 0) },
      );

      expect(get(totalPnl)?.toNumber()).toBe(50);
    });
  });

  it('should follow the statistics activity for its loading state', () => {
    isActive.current = true;

    expect(get(setup(statistic()).loading)).toBe(true);
  });
});
