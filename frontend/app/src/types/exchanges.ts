import { AssetBalance, type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';
import { type Collection, CollectionCommonFields } from '@/types/collection';
import type { AssetBalances } from '@/types/balances';
import type { PaginationRequestPayload } from '@/types/common';

export const KrakenAccountType = z.enum(['starter', 'intermediate', 'pro']);

export type KrakenAccountType = z.infer<typeof KrakenAccountType>;

export const Exchange = z.object({
  location: z.string(),
  name: z.string(),
  krakenAccountType: KrakenAccountType.optional(),
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

export interface ExchangeSetupPayload {
  readonly edit: boolean;
  readonly exchange: ExchangePayload;
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
  readonly newName: string;
}

const ExchangeSavingsEvent = AssetBalance.extend({
  timestamp: z.number(),
  location: z.string(),
});

export type ExchangeSavingsEvent = z.infer<typeof ExchangeSavingsEvent>;

export const ExchangeSavingsCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(ExchangeSavingsEvent),
  totalUsdValue: NumericString,
  assets: z.array(z.string()),
  received: z.array(AssetBalance),
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
