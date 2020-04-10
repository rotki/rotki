export type DSRMovementType = 'withdrawal' | 'deposit';

export enum Location {
  EXTERNAL = 'external',
  KRAKEN = 'kraken',
  POLONIEX = 'poloniex',
  BITTREX = 'bittrex',
  BINANCE = 'binance',
  BITMEX = 'bitmex',
  COINBASE = 'coinbase',
  TOTAL = 'total',
  BANKS = 'banks',
  BLOCKCHAIN = 'blockchain',
  COINBASEPRO = 'coinbasepro',
  GEMINI = 'gemini'
}

export interface SupportedAsset {
  readonly active: boolean;
  readonly ended: number;
  readonly name: string;
  readonly started: number;
  readonly symbol: string;
  readonly type: string;
}
