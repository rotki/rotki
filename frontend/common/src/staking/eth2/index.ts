import { z } from 'zod';
import { type GeneralAccount } from '../../account';
import { Balance, NumericString, Percentage } from '../../index';

const Eth2DailyStat = z.object({
  validatorIndex: z.number().nonnegative(),
  timestamp: z.number().nonnegative(),
  pnl: Balance
});

export type Eth2DailyStat = z.infer<typeof Eth2DailyStat>;

export const Eth2DailyStats = z.object({
  entries: z.array(Eth2DailyStat),
  entriesFound: z.number().nonnegative(),
  entriesTotal: z.number().nonnegative(),
  sumPnl: Balance
});

export type Eth2DailyStats = z.infer<typeof Eth2DailyStats>;

const Eth2Detail = z.object({
  eth1Depositor: z.string().nullable(),
  publicKey: z.string(),
  index: z.number(),
  hasExited: z.boolean(),
  balance: Balance,
  performance1d: Balance,
  performance1w: Balance,
  performance1m: Balance,
  performance1y: Balance,
  performanceTotal: Balance
});

export type Eth2Detail = z.infer<typeof Eth2Detail>;

export const Eth2Details = z.array(Eth2Detail);

export type Eth2Details = z.infer<typeof Eth2Details>;

export interface Eth2DailyStatsPayload {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttributes: string[];
  readonly ascending: boolean[];
  readonly validators?: number[];
  readonly fromTimestamp?: string;
  readonly toTimestamp?: string;
  readonly onlyCache?: boolean;
}

export interface EthStakingPayload {
  validatorIndices?: number[];
  addresses?: string[];
  ignoreCache?: boolean;
}

export interface EthStakingRewardsPayload
  extends EthStakingPayload,
    EthStakingPeriod {}

const Validator = z.object({
  validatorIndex: z.number(),
  publicKey: z.string(),
  ownershipPercentage: Percentage
});

export type Eth2ValidatorEntry = z.infer<typeof Validator>;

export const Eth2Validators = z.object({
  entries: z.array(Validator),
  entriesFound: z.number().nonnegative(),
  entriesLimit: z.number().min(-1)
});

export type Eth2Validators = z.infer<typeof Eth2Validators>;

export const Eth2StakingRewards = z.object({
  withdrawnConsensusLayerRewards: NumericString,
  executionLayerRewards: NumericString
});

export type Eth2StakingRewards = z.infer<typeof Eth2StakingRewards>;

export interface Eth2StakingFilter {
  accounts: GeneralAccount[];
  validators: Eth2ValidatorEntry[];
}

export type Eth2StakingFilterType = 'address' | 'validator';

export type EthStakingPeriod = {
  fromTimestamp?: string;
  toTimestamp?: string;
};
