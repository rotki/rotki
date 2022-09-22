import { BigNumber } from '@rotki/common';
import { z } from 'zod';
import { Nullable } from '@/types';
import { AssetBalances } from '@/types/balances';

export const KrakenAccountType = z.enum(['starter', 'intermediate', 'pro']);
export type KrakenAccountType = z.infer<typeof KrakenAccountType>;

export enum SupportedExchange {
  POLONIEX = 'poloniex',
  KRAKEN = 'kraken',
  BITTREX = 'bittrex',
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
  FTX = 'ftx',
  FTXUS = 'ftxus',
  INDEPENDENTRESERVE = 'independentreserve',
  GEMINI = 'gemini'
}

const SupportedExchangeType = z.nativeEnum(SupportedExchange);

export const SUPPORTED_EXCHANGES = Object.values(SupportedExchange);

export const Exchange = z.object({
  location: SupportedExchangeType,
  name: z.string(),
  krakenAccountType: KrakenAccountType.optional(),
  ftxSubaccount: z.string().optional()
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
  readonly edit: Boolean;
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
  readonly ftxSubaccount: Nullable<string>;
}
