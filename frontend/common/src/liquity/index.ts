import { z } from 'zod/v4';
import { AssetBalance } from '../balances';
import { NumericString } from '../numbers';

const LiquityBalance = z.object({
  active: z.boolean(),
  collateral: AssetBalance,
  collateralizationRatio: NumericString.nullable(),
  debt: AssetBalance,
  liquidationPrice: NumericString.nullable(),
  troveId: z.number(),
});

const LiquityBalances = z.record(z.string(), LiquityBalance);

export const LiquityBalancesWithCollateralInfo = z.object({
  balances: LiquityBalances,
  totalCollateralRatio: NumericString.nullable(),
});

export type LiquityBalancesWithCollateralInfo = z.infer<typeof LiquityBalancesWithCollateralInfo>;

export const LiquityStakingDetailEntry = z.object({
  ethRewards: AssetBalance,
  lusdRewards: AssetBalance,
  staked: AssetBalance,
});

export type LiquityStakingDetailEntry = z.infer<typeof LiquityStakingDetailEntry>;

const LiquityStakingDetailProxyEntries = z.record(z.string(), LiquityStakingDetailEntry);

const LiquityStakingDetail = z.object({
  balances: LiquityStakingDetailEntry.nullable(),
  proxies: LiquityStakingDetailProxyEntries.nullable(),
});

export const LiquityStakingDetails = z.record(z.string(), LiquityStakingDetail);

export type LiquityStakingDetails = z.infer<typeof LiquityStakingDetails>;

export const LiquityPoolDetailEntry = z.object({
  deposited: AssetBalance,
  gains: AssetBalance,
  rewards: AssetBalance,
});

export type LiquityPoolDetailEntry = z.infer<typeof LiquityPoolDetailEntry>;

const LiquityPoolDetailProxyEntries = z.record(z.string(), LiquityPoolDetailEntry);

const LiquityPoolDetail = z.object({
  balances: LiquityPoolDetailEntry.nullable(),
  proxies: LiquityPoolDetailProxyEntries.nullable(),
});

export const LiquityPoolDetails = z.record(z.string(), LiquityPoolDetail);

export type LiquityPoolDetails = z.infer<typeof LiquityPoolDetails>;

export const LiquityStatisticDetails = z.object({
  stabilityPoolGains: z.array(AssetBalance),
  stakingGains: z.array(AssetBalance),
  totalDepositedStabilityPool: NumericString,
  totalDepositedStabilityPoolValue: NumericString,
  totalValueGainsStabilityPool: NumericString,
  totalValueGainsStaking: NumericString,
  totalWithdrawnStabilityPool: NumericString,
  totalWithdrawnStabilityPoolValue: NumericString,
});

export type LiquityStatisticDetails = z.infer<typeof LiquityStatisticDetails>;

export const LiquityStatistics = z.object({
  byAddress: z.record(z.string(), LiquityStatisticDetails).optional(),
  globalStats: LiquityStatisticDetails.optional(),
});

export type LiquityStatistics = z.infer<typeof LiquityStatistics>;
