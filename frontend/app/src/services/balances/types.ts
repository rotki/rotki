import { z } from 'zod';
import { type EXTERNAL_EXCHANGES } from '@/data/defaults';

export type SupportedExternalExchanges = typeof EXTERNAL_EXCHANGES[number];

export enum BalanceType {
  ASSET = 'asset',
  LIABILITY = 'liability'
}

export interface OracleCacheMeta {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly fromTimestamp: string;
  readonly toTimestamp: string;
}

export const EthDetectedTokens = z.object({
  tokens: z.array(z.string()).nullish(),
  lastUpdateTimestamp: z.number().nullish()
});

export const EthDetectedTokensRecord = z.record(EthDetectedTokens);

export type EthDetectedTokensRecord = z.infer<typeof EthDetectedTokensRecord>;

export interface EthDetectedTokensInfo {
  tokens: string[];
  total: number;
  timestamp: number | null;
}
