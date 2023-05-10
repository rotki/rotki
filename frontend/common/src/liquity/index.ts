import { z } from 'zod';
import { AssetBalance, NumericString } from '../index';

const LiquityBalance = z.object({
  collateral: AssetBalance,
  debt: AssetBalance,
  collateralizationRatio: NumericString.nullable(),
  liquidationPrice: NumericString.nullable(),
  active: z.boolean(),
  troveId: z.number()
});

export type LiquityBalance = z.infer<typeof LiquityBalance>;

export const LiquityBalances = z.record(LiquityBalance);

export type LiquityBalances = z.infer<typeof LiquityBalances>;

export const LiquityStakingDetailEntry = z.object({
  ethRewards: AssetBalance,
  lusdRewards: AssetBalance,
  staked: AssetBalance
});

export type LiquityStakingDetailEntry = z.infer<
  typeof LiquityStakingDetailEntry
>;

export const LiquityStakingDetailProxyEntries = z.record(
  LiquityStakingDetailEntry
);

export type LiquityStakingDetailProxyEntries = z.infer<
  typeof LiquityStakingDetailProxyEntries
>;

export const LiquityStakingDetail = z.object({
  balances: LiquityStakingDetailEntry.nullable(),
  proxies: LiquityStakingDetailProxyEntries.nullable()
});
export const LiquityStakingDetails = z.record(LiquityStakingDetail);

export type LiquityStakingDetails = z.infer<typeof LiquityStakingDetails>;

export const LiquityPoolDetailEntry = z.object({
  gains: AssetBalance,
  rewards: AssetBalance,
  deposited: AssetBalance
});

export type LiquityPoolDetailEntry = z.infer<typeof LiquityPoolDetailEntry>;

export const LiquityPoolDetailProxyEntries = z.record(LiquityPoolDetailEntry);

export type LiquityPoolDetailProxyEntries = z.infer<
  typeof LiquityPoolDetailProxyEntries
>;

export const LiquityPoolDetail = z.object({
  balances: LiquityPoolDetailEntry.nullable(),
  proxies: LiquityPoolDetailProxyEntries.nullable()
});
export const LiquityPoolDetails = z.record(LiquityPoolDetail);

export type LiquityPoolDetails = z.infer<typeof LiquityPoolDetails>;

export const LiquityStatisticDetails = z.object({
  totalUsdGainsStabilityPool: NumericString,
  totalUsdGainsStaking: NumericString,
  totalDepositedStabilityPool: NumericString,
  totalWithdrawnStabilityPool: NumericString,
  totalDepositedStabilityPoolUsdValue: NumericString,
  totalWithdrawnStabilityPoolUsdValue: NumericString,
  stakingGains: z.array(AssetBalance),
  stabilityPoolGains: z.array(AssetBalance)
});

export type LiquityStatisticDetails = z.infer<typeof LiquityStatisticDetails>;

export const LiquityStatistics = z.object({
  globalStats: LiquityStatisticDetails,
  byAddress: z.record(z.string(), LiquityStatisticDetails).optional()
});

export type LiquityStatistics = z.infer<typeof LiquityStatistics>;
