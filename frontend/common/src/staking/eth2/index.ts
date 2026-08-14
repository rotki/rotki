import type { Account } from '../../account';
import { z } from 'zod';
import { Percentage } from '../../balances';
import { type BigNumber, NumericString } from '../../numbers';

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
  validators: z.record(z.string(), EthStakingStats),
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

/**
 * Every status a validator can be filtered by, as values rather than a bare union: the app offers
 * them in a filter and has to enumerate them at runtime. It used to keep its own copy of this list
 * beside the union here, so a status added on one side left the other silently offering a stale set.
 *
 * `all` is the absence of a filter rather than a status a validator holds.
 */
export const ethValidatorStatuses = ['all', 'exited', 'active', 'consolidated'] as const;

export type EthValidatorStatus = typeof ethValidatorStatuses[number];

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
  readonly ignoreCache?: boolean;
}
