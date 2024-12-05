import { Balance, NumericString } from '@rotki/common';
import { z } from 'zod';

const DefiProtocolInfo = z.object({
  name: z.string(),
});

const TokenInfo = z.object({
  tokenName: z.string(),
  tokenSymbol: z.string(),
});

const DefiAsset = z.object({
  balance: Balance,
  tokenAddress: z.string(),
  tokenName: z.string(),
  tokenSymbol: z.string(),
});

export type DefiAsset = z.infer<typeof DefiAsset>;

const DefiProtocolSummary = z.object({
  assets: z.array(DefiAsset),
  balanceUsd: NumericString.optional(),
  deposits: z.boolean(),
  depositsUrl: z.string().optional(),
  liabilities: z.boolean(),
  liabilitiesUrl: z.string().optional(),
  protocol: z.string(),
  tokenInfo: TokenInfo.nullable(),
  totalCollateralUsd: NumericString,
  totalDebtUsd: NumericString,
  totalLendingDepositUsd: NumericString,
});

export type DefiProtocolSummary = z.infer<typeof DefiProtocolSummary>;

const DefiProtocolData = z.object({
  balanceType: z.enum(['Asset', 'Debt'] as const),
  baseBalance: DefiAsset,
  protocol: DefiProtocolInfo,
  underlyingBalances: z.array(DefiAsset),
});

export const AllDefiProtocols = z.record(z.array(DefiProtocolData));

export type AllDefiProtocols = z.infer<typeof AllDefiProtocols>;
