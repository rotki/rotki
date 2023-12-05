import { AssetBalance, type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';
import { type Nullable } from '@/types';
import { type AssetBalances } from '@/types/balances';
import { type EXTERNAL_EXCHANGES } from '@/data/defaults';
import { type PaginationRequestPayload } from '@/types/common';
import { type Collection, CollectionCommonFields } from '@/types/collection';

export const KrakenAccountType = z.enum(['starter', 'intermediate', 'pro']);

export type KrakenAccountType = z.infer<typeof KrakenAccountType>;

export enum SupportedExchange {
  POLONIEX = 'poloniex',
  KRAKEN = 'kraken',
  BITMEX = 'bitmex',
  BITPANDA = 'bitpanda',
  BITFINEX = 'bitfinex',
  BINANCE = 'binance',
  COINBASE = 'coinbase',
  COINBASEPRO = 'coinbasepro',
  BITSTAMP = 'bitstamp',
  BINANCEUS = 'binanceus',
  BITCOIN_DE = 'bitcoinde',
  ICONOMI = 'iconomi',
  KUCOIN = 'kucoin',
  INDEPENDENTRESERVE = 'independentreserve',
  GEMINI = 'gemini',
  OKX = 'okx',
  WOO = 'woo',
  BYBIT = 'bybit'
}

const SupportedExchangeType = z.nativeEnum(SupportedExchange);

export const SUPPORTED_EXCHANGES = Object.values(SupportedExchange);

export type SupportedExternalExchanges = (typeof EXTERNAL_EXCHANGES)[number];

export const Exchange = z.object({
  location: SupportedExchangeType,
  name: z.string(),
  krakenAccountType: KrakenAccountType.optional()
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
  readonly newName: Nullable<string>;
}

export interface ExchangeSetupPayload {
  readonly edit: boolean;
  readonly exchange: ExchangePayload;
}

export interface ExchangePayload {
  readonly name: string;
  readonly newName: Nullable<string>;
  readonly location: SupportedExchange;
  readonly apiKey: Nullable<string>;
  readonly apiSecret: Nullable<string>;
  readonly passphrase: Nullable<string>;
  readonly krakenAccountType: Nullable<KrakenAccountType>;
  readonly binanceMarkets: Nullable<string[]>;
}

const ExchangeSavingsEvent = AssetBalance.extend({
  timestamp: z.number(),
  location: z.string()
});

export type ExchangeSavingsEvent = z.infer<typeof ExchangeSavingsEvent>;

export const ExchangeSavingsCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(ExchangeSavingsEvent),
  totalUsdValue: NumericString,
  assets: z.array(z.string()),
  received: z.array(AssetBalance)
});

export type ExchangeSavingsCollectionResponse = z.infer<
  typeof ExchangeSavingsCollectionResponse
>;

export interface ExchangeSavingsCollection
  extends Collection<ExchangeSavingsEvent> {
  assets: string[];
  received: AssetBalance[];
}

export interface ExchangeSavingsRequestPayload
  extends PaginationRequestPayload<ExchangeSavingsEvent> {
  readonly location: string;
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
}
