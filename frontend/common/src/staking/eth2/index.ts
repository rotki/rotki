import { z } from 'zod';
import { Balance, NumericString, Percentage } from '../../index';

export const Eth2Deposit = z.object({
  fromAddress: z.string(),
  pubkey: z.string(),
  withdrawalCredentials: z.string(),
  value: Balance,
  txHash: z.string(),
  timestamp: z.number(),
  txIndex: z.number().nonnegative()
});

export type Eth2Deposit = z.infer<typeof Eth2Deposit>;

export const Eth2Deposits = z.array(Eth2Deposit);

export type Eth2Deposits = z.infer<typeof Eth2Deposits>;

const Eth2DailyStat = z.object({
  validatorIndex: z.number().nonnegative(),
  timestamp: z.number().nonnegative(),
  pnl: Balance,
  startBalance: Balance,
  endBalance: Balance,
  missedAttestations: z.number().nonnegative(),
  orphanedAttestations: z.number().nonnegative(),
  proposedBlocks: z.number().nonnegative(),
  missedBlocks: z.number().nonnegative(),
  orphanedBlocks: z.number().nonnegative(),
  includedAttesterSlashings: z.number().nonnegative(),
  proposerAttesterSlashings: z.number().nonnegative(),
  depositsNumber: z.number().nonnegative(),
  depositedBalance: Balance
});

export type Eth2DailyStat = z.infer<typeof Eth2DailyStat>;

export const Eth2DailyStats = z.object({
  entries: z.array(Eth2DailyStat),
  entriesFound: z.number().nonnegative(),
  entriesTotal: z.number().nonnegative(),
  sumPnl: NumericString,
  sumUsdValue: NumericString
});

export type Eth2DailyStats = z.infer<typeof Eth2DailyStats>;

const Eth2Detail = z.object({
  eth1Depositor: z.string(),
  publicKey: z.string(),
  index: z.number(),
  balance: Balance,
  performance1d: Balance,
  performance1w: Balance,
  performance1m: Balance,
  performance1y: Balance
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
  readonly fromTimestamp?: number;
  readonly toTimestamp?: number;
  readonly onlyCache?: boolean;
}

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
