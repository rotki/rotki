// Trades
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { getCollectionResponseType } from '@/types/collection';
import { HistoryRequestPayload } from '@/types/history/index';
import { getEntryWithMeta } from '@/types/history/meta';
import { TradeLocation } from '@/types/history/trade-location';

export const TradeType = z.enum([
  'buy',
  'sell',
  'settlement buy',
  'settlement sell'
]);
export type TradeType = z.infer<typeof TradeType>;
export const Trade = z.object({
  tradeId: z.string(),
  timestamp: z.number(),
  location: TradeLocation,
  baseAsset: z.string(),
  quoteAsset: z.string(),
  tradeType: TradeType,
  amount: NumericString,
  rate: NumericString,
  fee: NumericString.nullish(),
  feeCurrency: z.string().nullish(),
  link: z.string().nullish(),
  notes: z.string().nullish()
});
export type Trade = z.infer<typeof Trade>;
export const TradeCollectionResponse = getCollectionResponseType(
  getEntryWithMeta(Trade)
);
export type NewTrade = Omit<Trade, 'tradeId' | 'ignoredInAccounting'>;
export type TradeRequestPayload = {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly baseAsset?: string;
  readonly quoteAsset?: string;
  readonly tradeType?: string;
} & HistoryRequestPayload<Trade>;
