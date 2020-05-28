export type DSRMovementType = 'withdrawal' | 'deposit';

export enum Location {
  EXTERNAL = 'external',
  KRAKEN = 'kraken',
  POLONIEX = 'poloniex',
  BITTREX = 'bittrex',
  BINANCE = 'binance',
  BITMEX = 'bitmex',
  COINBASE = 'coinbase',
  BANKS = 'banks',
  BLOCKCHAIN = 'blockchain',
  COINBASEPRO = 'coinbasepro',
  GEMINI = 'gemini',
  EQUITIES = 'equities',
  REALESTATE = 'real estate',
  COMMODITIES = 'commodities'
}

export type MakerDAOVaultEventType =
  | 'deposit'
  | 'withdraw'
  | 'generate'
  | 'payback'
  | 'liquidation';

export type CollateralAssetType = 'ETH' | 'BAT' | 'USDC' | 'WBTC';
