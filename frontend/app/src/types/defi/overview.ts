import { Balance, NumericString } from '@rotki/common';
import { z } from 'zod';

const DefiProtocolInfo = z.object({
  name: z.string()
});

const TokenInfo = z.object({
  tokenName: z.string(),
  tokenSymbol: z.string()
});

export type TokenInfo = z.infer<typeof TokenInfo>;

const DefiAsset = z.object({
  balance: Balance,
  tokenAddress: z.string(),
  tokenName: z.string(),
  tokenSymbol: z.string()
});

export type DefiAsset = z.infer<typeof DefiAsset>;

const DefiProtocolSummary = z.object({
  protocol: z.string(),
  balanceUsd: NumericString.optional(),
  assets: z.array(DefiAsset),
  tokenInfo: TokenInfo.nullable(),
  deposits: z.boolean(),
  liabilities: z.boolean(),
  depositsUrl: z.string().optional(),
  liabilitiesUrl: z.string().optional(),
  totalCollateralUsd: NumericString,
  totalDebtUsd: NumericString,
  totalLendingDepositUsd: NumericString
});

export type DefiProtocolSummary = z.infer<typeof DefiProtocolSummary>;

const DefiProtocolData = z.object({
  protocol: DefiProtocolInfo,
  balanceType: z.enum(['Asset', 'Debt'] as const),
  baseBalance: DefiAsset,
  underlyingBalances: z.array(DefiAsset)
});

export const AllDefiProtocols = z.record(z.array(DefiProtocolData));

export type AllDefiProtocols = z.infer<typeof AllDefiProtocols>;
