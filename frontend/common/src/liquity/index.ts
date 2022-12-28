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

const TroveEvent = z.object({
  kind: z.literal('trove'),
  sequenceNumber: z.string(),
  tx: z.string(),
  address: z.string(),
  timestamp: z.number(),
  debtAfter: AssetBalance,
  debtDelta: AssetBalance,
  collateralAfter: AssetBalance,
  collateralDelta: AssetBalance,
  troveOperation: z.string()
});

export type TroveEvent = z.infer<typeof TroveEvent>;

export const TroveEvents = z.record(z.array(TroveEvent));

export type TroveEvents = z.infer<typeof TroveEvents>;

export const LiquityStakingDetail = z.object({
  ethRewards: AssetBalance,
  lusdRewards: AssetBalance,
  staked: AssetBalance
});

export type LiquityStakingDetail = z.infer<typeof LiquityStakingDetail>;

export const LiquityStakingDetails = z.record(LiquityStakingDetail);

export type LiquityStakingDetails = z.infer<typeof LiquityStakingDetails>;

export const LiquityPoolDetail = z.object({
  gains: AssetBalance,
  rewards: AssetBalance,
  deposited: AssetBalance
});

export type LiquityPoolDetail = z.infer<typeof LiquityPoolDetail>;

export const LiquityPoolDetails = z.record(LiquityPoolDetail);

export type LiquityPoolDetails = z.infer<typeof LiquityPoolDetails>;
