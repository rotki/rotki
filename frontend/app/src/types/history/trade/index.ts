// Trades
import type { PaginationRequestPayload } from '@/types/common';
import { CollectionCommonFields } from '@/types/collection';
import { EntryMeta } from '@/types/history/meta';
import { NumericString } from '@rotki/common';

import { z } from 'zod';

export enum TradeType {
  BUY = 'buy',
  SELL = 'sell',
  SETTLEMENT_BUY = 'settlement buy',
  SETTLEMENT_SELL = 'settlement sell',
}

export const TradeTypeEnum = z.nativeEnum(TradeType);

export type TradeTypeEnum = z.infer<typeof TradeTypeEnum>;

export const Trade = z.object({
  amount: NumericString,
  baseAsset: z.string(),
  fee: NumericString.nullable(),
  feeCurrency: z.string().nullable(),
  link: z.string().nullable(),
  location: z.string(),
  notes: z.string().nullable(),
  quoteAsset: z.string(),
  rate: NumericString,
  timestamp: z.number(),
  tradeId: z.string(),
  tradeType: TradeTypeEnum,
});

export type Trade = z.infer<typeof Trade>;

export const TradeCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(
    z
      .object({
        entry: Trade,
      })
      .merge(EntryMeta),
  ),
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
