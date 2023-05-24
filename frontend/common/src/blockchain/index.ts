export enum Blockchain {
  ETH = 'eth',
  ETH2 = 'eth2',
  BTC = 'btc',
  BCH = 'bch',
  KSM = 'ksm',
  DOT = 'dot',
  AVAX = 'avax',
  OPTIMISM = 'optimism'
}

export type BlockchainSelection = Blockchain | 'ALL';

export enum DefiProtocol {
  YEARN_VAULTS = 'yearn_vaults',
  YEARN_VAULTS_V2 = 'yearn_vaults_v2',
  AAVE = 'aave',
  MAKERDAO_DSR = 'makerdao_dsr',
  MAKERDAO_VAULTS = 'makerdao_vaults',
  COMPOUND = 'compound',
  UNISWAP = 'uniswap',
  LIQUITY = 'liquity'
}
