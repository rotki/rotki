import type { Account } from '../../account';
import { z } from 'zod';
import { Balance, Percentage } from '../../balances';
import { type BigNumber, NumericString } from '../../numbers';

const Eth2DailyStat = z.object({
  pnl: Balance,
  timestamp: z.number().nonnegative(),
  validatorIndex: z.number().nonnegative(),
});

export type Eth2DailyStat = z.infer<typeof Eth2DailyStat>;

type EthStakingDailyStats = Eth2DailyStat & { ownershipPercentage?: string };

export const Eth2DailyStats = z.object({
  entries: z.array(Eth2DailyStat),
  entriesFound: z.number().nonnegative(),
  entriesTotal: z.number().nonnegative(),
  sumPnl: NumericString,
});

export type Eth2DailyStats = z.infer<typeof Eth2DailyStats>;

export type EthStakingDailyStatData = Omit<Eth2DailyStats, 'entries'> & {
  entries: EthStakingDailyStats[];
};

const EthStakingStats = z.object({
  apr: NumericString.optional(),
  executionBlocks: NumericString.optional(),
  executionMev: NumericString.optional(),
  exits: NumericString.optional(),
  outstandingConsensusPnl: NumericString.optional(),
  sum: NumericString.optional(),
  withdrawals: NumericString.optional(),
});

type EthStakingStats = z.infer<typeof EthStakingStats>;

export const EthStakingPerformanceResponse = z.object({
  entriesFound: z.number(),
  entriesTotal: z.number(),
  sums: EthStakingStats,
  validators: z.record(EthStakingStats),
});

export type EthStakingPerformanceResponse = z.infer<typeof EthStakingPerformanceResponse>;

type EthStakingValidatorPerformance = EthStakingStats & {
  index: number;
  status?: string;
  total?: BigNumber;
};

export type EthStakingPerformance = Omit<EthStakingPerformanceResponse, 'validators'> & {
  validators: EthStakingValidatorPerformance[];
};

export type EthValidatorStatus = 'all' | 'exited' | 'active' | 'consolidated';

export interface EthStakingPayload extends EthStakingPeriod {
  limit: number;
  offset: number;
  validatorIndices?: number[];
  addresses?: string[];
  status?: EthValidatorStatus;
}

const Validator = z.object({
  activationTimestamp: z.number().nonnegative().optional(),
  consolidatedInto: z.number().nonnegative().optional(),
  index: z.number(),
  ownershipPercentage: Percentage.optional(),
  publicKey: z.string(),
  status: z.string(),
  withdrawableTimestamp: z.number().nonnegative().optional(),
  withdrawalAddress: z.string().optional(),
});

export type Eth2ValidatorEntry = z.infer<typeof Validator>;

export const Eth2Validators = z.object({
  entries: z.array(Validator),
  entriesFound: z.number().nonnegative(),
  entriesLimit: z.number().min(-1),
});

export type Eth2Validators = z.infer<typeof Eth2Validators>;

interface EthStakingDepositorFilter {
  accounts: Account[];
}

interface EthStakingValidatorFilter {
  validators: Eth2ValidatorEntry[];
}

export type EthStakingFilter = EthStakingDepositorFilter | EthStakingValidatorFilter;

export type EthStakingFilterType = 'address' | 'validator';

export interface EthStakingPeriod {
  fromTimestamp?: number;
  toTimestamp?: number;
}

export interface EthStakingCombinedFilter extends EthStakingPeriod {
  status?: EthValidatorStatus;
}

export interface EthValidatorFilter {
  readonly validatorIndices?: number[];
  readonly addresses?: string[];
  readonly status?: EthValidatorStatus;
}

export interface Eth2DailyStatsPayload extends EthStakingPeriod {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttributes: string[];
  readonly ascending: boolean[];
  readonly validatorIndices?: number[];
  readonly addresses?: string[];
  readonly onlyCache?: boolean;
}
