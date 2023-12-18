// Trades
import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { type PaginationRequestPayload } from '@/types/common';
import { EntryMeta } from '@/types/history/meta';
import { CollectionCommonFields } from '@/types/collection';

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
  location: z.string(),
  baseAsset: z.string(),
  quoteAsset: z.string(),
  tradeType: TradeType,
  amount: NumericString,
  rate: NumericString,
  fee: NumericString.nullable(),
  feeCurrency: z.string().nullable(),
  link: z.string().nullable(),
  notes: z.string().nullable()
});

export type Trade = z.infer<typeof Trade>;

export const TradeCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(
    z
      .object({
        entry: Trade
      })
      .merge(EntryMeta)
  )
});

export type NewTrade = Omit<Trade, 'tradeId' | 'ignoredInAccounting'>;

export interface TradeRequestPayload extends PaginationRequestPayload<Trade> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly location?: string;
  readonly baseAsset?: string;
  readonly quoteAsset?: string;
  readonly tradeType?: string;
  readonly includeIgnoredTrades?: boolean;
  readonly excludeIgnoredAssets?: boolean;
}

export interface TradeEntry extends Trade, EntryMeta {}
