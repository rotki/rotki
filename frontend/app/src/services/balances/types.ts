import { z } from 'zod';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';

export type SupportedExternalExchanges = typeof EXTERNAL_EXCHANGES[number];

export enum BalanceType {
  ASSET = 'asset',
  LIABILITY = 'liability'
}

export type OracleCacheMeta = {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly fromTimestamp: string;
  readonly toTimestamp: string;
};

export const EthDetectedTokens = z.object({
  tokens: z.array(z.string()).nullish(),
  lastUpdateTimestamp: z.number().nullish()
});

export const EthDetectedTokensRecord = z.record(EthDetectedTokens);

export type EthDetectedTokensRecord = z.infer<typeof EthDetectedTokensRecord>;

export type EthDetectedTokensInfo = {
  tokens: string[];
  total: number;
  timestamp: number | null;
};
