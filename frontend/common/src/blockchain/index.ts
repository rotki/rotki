export enum Blockchain {
  ETH = 'ETH',
  ETH2 = 'ETH2',
  BTC = 'BTC',
  BCH = 'BCH',
  KSM = 'KSM',
  DOT = 'DOT',
  AVAX = 'AVAX',
  OPTIMISM = 'OPTIMISM'
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
