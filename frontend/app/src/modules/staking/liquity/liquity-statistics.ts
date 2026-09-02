import {
  type AssetBalance,
  type BigNumber,
  type LiquityPoolDetailEntry,
  type LiquityStatisticDetails,
  One,
  Zero,
} from '@rotki/common';
import { bigNumberSum } from '@/modules/core/common/data/calculation';

/** Which prices the statistics are shown at: those recorded at the time, or today's. */
export const StatisticView = {
  CURRENT: 'current',
  HISTORICAL: 'historical',
} as const;

export type StatisticView = typeof StatisticView[keyof typeof StatisticView];

/** Resolves an asset's price, or `undefined` when it has none. */
export type PriceLookup = (asset: string) => BigNumber | undefined;

/**
 * A usable multiplier for an amount.
 *
 * @returns the price, or 1 when there is none or it is zero, so the amount is left unscaled rather
 * than collapsed to nothing
 */
export function orOne(price: BigNumber | undefined): BigNumber {
  return price?.gt(0) ? price : One;
}

/** {@link orOne} for an asset whose price has to be looked up. */
export function priceOrOne(priceOf: PriceLookup, asset: string): BigNumber {
  return orOne(priceOf(asset));
}

/**
 * Re-values gains at today's price.
 *
 * @remarks
 * No price and a zero price differ: an unpriced asset is multiplied by 1 and keeps its amount as
 * its value, while one priced at zero is worth zero.
 */
function repriceGains(gains: AssetBalance[], priceOf: PriceLookup): AssetBalance[] {
  return gains.map((gain) => {
    const price = priceOf(gain.asset) ?? One;
    return {
      ...gain,
      value: price.gt(0) ? gain.amount.multipliedBy(price) : Zero,
    };
  });
}

/**
 * The statistics for the chosen view.
 *
 * @param statistic - the recorded figures to reprice
 * @param view - `historical` returns them untouched; `current` re-values every gain and both LUSD
 * totals at today's prices
 * @param priceOf - resolves an asset's current price
 * @param lusdPrice - already resolved, since the stability pool totals are denominated in LUSD
 */
export function repriceStatistic(
  statistic: LiquityStatisticDetails,
  view: StatisticView,
  priceOf: PriceLookup,
  lusdPrice: BigNumber,
): LiquityStatisticDetails {
  if (view === StatisticView.HISTORICAL)
    return statistic;

  const stakingGains = repriceGains(statistic.stakingGains, priceOf);
  const stabilityPoolGains = repriceGains(statistic.stabilityPoolGains, priceOf);

  return {
    ...statistic,
    stabilityPoolGains,
    stakingGains,
    totalDepositedStabilityPoolValue: statistic.totalDepositedStabilityPool.multipliedBy(lusdPrice),
    totalValueGainsStabilityPool: bigNumberSum(stabilityPoolGains.map(({ value }) => value)),
    totalValueGainsStaking: bigNumberSum(stakingGains.map(({ value }) => value)),
    totalWithdrawnStabilityPoolValue: statistic.totalWithdrawnStabilityPool.multipliedBy(lusdPrice),
  };
}

/**
 * Estimated profit or loss on the stability pool.
 *
 * @remarks
 * The difference between what came out and what went missing:
 *
 * - `A` = deposited - withdrawn, the LUSD that should still be in the pool
 * - `B` = recorded gains + liquidation gains + rewards, all at today's price
 * - `C` = (A - what is actually deposited now) at today's LUSD price, the LUSD consumed by
 *   liquidations
 * - PnL = B - C
 */
export function calculatePnl(
  statistic: LiquityStatisticDetails,
  pool: LiquityPoolDetailEntry,
  priceOf: PriceLookup,
  lusdPrice: BigNumber,
): BigNumber {
  const expectedAmount = statistic.totalDepositedStabilityPool.minus(statistic.totalWithdrawnStabilityPool);

  const liquidationGains = pool.gains.amount.multipliedBy(priceOrOne(priceOf, pool.gains.asset));
  const rewards = pool.rewards.amount.multipliedBy(priceOrOne(priceOf, pool.rewards.asset));

  const totalWithdrawals = statistic.totalValueGainsStabilityPool
    .plus(liquidationGains)
    .plus(rewards);

  const consumed = expectedAmount.minus(pool.deposited.amount).multipliedBy(lusdPrice);

  return totalWithdrawals.minus(consumed);
}
