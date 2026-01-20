import { Blockchain } from '@rotki/common';
import { z } from 'zod/v4';

export const AccountingRuleConflictData = z.object({
  numOfConflicts: z.number(),
});

export type AccountingRuleConflictData = z.infer<typeof AccountingRuleConflictData>;

export const ExchangeUnknownAssetData = z.object({
  details: z.string(),
  identifier: z.string(),
  location: z.string(),
  name: z.string(),
});

export type ExchangeUnknownAssetData = z.infer<typeof ExchangeUnknownAssetData>;

const RefreshBalancesType = {
  BLOCKCHAIN_BALANCES: 'blockchain_balances',
} as const;

export const RefreshBalancesData = z.object({
  blockchain: z.enum(Blockchain),
  type: z.enum(RefreshBalancesType),
});

export type RefreshBalancesData = z.infer<typeof RefreshBalancesData>;
