import { z } from 'zod';

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
  INDEPENDENTRESERVE = 'independentreserve',
  GEMINI = 'gemini'
}

export const SupportedExchangeType = z.nativeEnum(SupportedExchange);
export type SupportedExchangeType = z.infer<typeof SupportedExchangeType>;

export const SUPPORTED_EXCHANGES = Object.values(SupportedExchange);

export const Exchange = z.object({
  location: SupportedExchangeType,
  name: z.string(),
  krakenAccountType: KrakenAccountType.optional(),
  ftxSubaccount: z.string().optional()
});

export type Exchange = z.infer<typeof Exchange>;
