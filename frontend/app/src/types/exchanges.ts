import type { AssetBalances } from '@/types/balances';
import type { PaginationRequestPayload } from '@/types/common';
import { type Collection, CollectionCommonFields } from '@/types/collection';
import { AssetBalance, type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod/v4';

export const KrakenAccountType = z.enum(['starter', 'intermediate', 'pro']);

export type KrakenAccountType = z.infer<typeof KrakenAccountType>;

export const Exchange = z.object({
  krakenAccountType: KrakenAccountType.optional(),
  location: z.string(),
  name: z.string(),
});

export type Exchange = z.infer<typeof Exchange>;

export const Exchanges = z.array(Exchange);

export type Exchanges = z.infer<typeof Exchanges>;

export interface ExchangeInfo {
  readonly location: string;
  readonly balances: AssetBalances;
  readonly total: BigNumber;
}

export type ExchangeData = Record<string, AssetBalances>;

export interface EditExchange {
  readonly exchange: Exchange;
  readonly newName?: string;
}

export interface ExchangePayload {
  readonly name: string;
  readonly location: string;
  readonly apiKey: string;
  readonly apiSecret: string;
  readonly passphrase: string;
  readonly krakenAccountType?: KrakenAccountType;
  readonly binanceMarkets?: string[];
}

export interface ExchangeFormData extends ExchangePayload {
  readonly mode: 'edit' | 'add';
  readonly newName?: string;
}

const ExchangeSavingsEvent = z.object({
  amount: NumericString,
  asset: z.string().min(1),
  location: z.string(),
  timestamp: z.number(),
});

export type ExchangeSavingsEvent = z.infer<typeof ExchangeSavingsEvent>;

export const ExchangeSavingsCollectionResponse = CollectionCommonFields.extend({
  assets: z.array(z.string()),
  entries: z.array(ExchangeSavingsEvent),
  received: z.array(AssetBalance),
  totalUsdValue: NumericString,
});

export type ExchangeSavingsCollectionResponse = z.infer<typeof ExchangeSavingsCollectionResponse>;

export interface ExchangeSavingsCollection extends Collection<ExchangeSavingsEvent> {
  assets: string[];
  received: AssetBalance[];
}

export interface ExchangeSavingsRequestPayload extends PaginationRequestPayload<ExchangeSavingsEvent> {
  readonly location: string;
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
}
