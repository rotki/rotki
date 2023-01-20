import { z } from 'zod';

export enum HistoryEventType {
  NONE = 'none',
  TRADE = 'trade',
  STAKING = 'staking',
  DEPOSIT = 'deposit',
  WITHDRAWAL = 'withdrawal',
  TRANSFER = 'transfer',
  SPEND = 'spend',
  RECEIVE = 'receive',
  ADJUSTMENT = 'adjustment',
  UNKNOWN = 'unknown',
  INFORMATIONAL = 'informational',
  MIGRATE = 'migrate',
  RENEW = 'renew'
}

export const HistoryEventTypeEnum = z.nativeEnum(HistoryEventType);
export type HistoryEventTypeEnum = z.infer<typeof HistoryEventTypeEnum>;

export enum HistoryEventSubType {
  NONE = 'none',
  REWARD = 'reward',
  DEPOSIT_ASSET = 'deposit asset',
  REMOVE_ASSET = 'remove asset',
  FEE = 'fee',
  SPEND = 'spend',
  RECEIVE = 'receive',
  APPROVE = 'approve',
  DEPLOY = 'deploy',
  AIRDROP = 'airdrop',
  BRIDGE = 'bridge',
  GOVERNANCE = 'governance',
  GENERATE_DEBT = 'generate debt',
  PAYBACK_DEBT = 'payback debt',
  RECEIVE_WRAPPED = 'receive wrapped',
  RETURN_WRAPPED = 'return wrapped',
  DONATE = 'donate',
  NFT = 'nft',
  PLACE_ORDER = 'place order',
  LIQUIDATE = 'liquidate'
}

export const HistoryEventSubTypeEnum = z.nativeEnum(HistoryEventSubType);
export type HistoryEventSubTypeEnum = z.infer<typeof HistoryEventSubTypeEnum>;

export enum TransactionEventType {
  GAS = 'gas',
  SEND = 'send',
  RECEIVE = 'receive',
  SWAP_OUT = 'swap_out',
  SWAP_IN = 'swap_in',
  APPROVAL = 'approval',
  DEPOSIT = 'deposit',
  WITHDRAW = 'withdraw',
  AIRDROP = 'airdrop',
  BORROW = 'borrow',
  REPAY = 'repay',
  DEPLOY = 'deploy',
  BRIDGE = 'bridge',
  GOVERNANCE = 'governance',
  DONATE = 'donate',
  RECEIVE_DONATION = 'receive_donation',
  RENEW = 'renew',
  PLACE_ORDER = 'place_order',
  TRANSFER = 'transfer',
  CLAIM_REWARD = 'claim_reward',
  LIQUIDATE = 'liquidate'
}

export const TransactionEventTypeEnum = z.nativeEnum(TransactionEventType);
export type TransactionEventTypeEnum = z.infer<typeof TransactionEventTypeEnum>;

export enum TransactionEventProtocol {
  '1INCH' = '1inch',
  AAVE = 'aave',
  BADGER = 'badger',
  COMPOUND = 'compound',
  CONVEX = 'convex',
  CURVE = 'curve',
  DXDAO = 'dxdao',
  ELEMENT_FINANCE = 'element-finance',
  ENS = 'ens',
  FRAX = 'frax',
  GAS = 'gas',
  GITCOIN = 'gitcoin',
  GNOSIS_CHAIN = 'gnosis-chain',
  HOP_PROTOCOL = 'hop-protocol',
  KRAKEN = 'kraken',
  KYBER_LEGACY = 'kyber legacy',
  LIQUITY = 'liquity',
  MAKERDAO = 'makerdao',
  OPTIMISM = 'optimism',
  PICKLE = 'pickle finance',
  SHAPESHIFT = 'shapeshift',
  SUSHISWAP = 'sushiswap',
  UNISWAP = 'uniswap',
  VOTIUM = 'votium',
  WETH = 'weth',
  XDAI = 'xdai',
  YEARN = 'yearn',
  ZKSYNC = 'zksync'
}
