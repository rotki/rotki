export enum Blockchain {
  ETH = 'eth',
  ETH2 = 'eth2',
  BTC = 'btc',
  BCH = 'bch',
  KSM = 'ksm',
  DOT = 'dot',
  AVAX = 'avax',
  OPTIMISM = 'optimism',
  POLYGON_POS = 'polygon_pos',
  ARBITRUM_ONE = 'arbitrum_one',
  BASE = 'base',
  GNOSIS = 'gnosis'
}

export type BlockchainSelection = Blockchain | 'ALL';
