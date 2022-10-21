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
  GOVERNANCE_PROPOSE = 'governance propose',
  GENERATE_DEBT = 'generate debt',
  PAYBACK_DEBT = 'payback debt',
  RECEIVE_WRAPPED = 'receive wrapped',
  RETURN_WRAPPED = 'return wrapped',
  DONATE = 'donate',
  NFT = 'nft',
  PLACE_ORDER = 'place order'
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
  GOVERNANCE_PROPOSE = 'governance_propose',
  DONATE = 'donate',
  RECEIVE_DONATION = 'receive_donation',
  RENEW = 'renew',
  PLACE_ORDER = 'place_order',
  TRANSFER = 'transfer',
  CLAIM_REWARD = 'claim_reward'
}

export const TransactionEventTypeEnum = z.nativeEnum(TransactionEventType);
export type TransactionEventTypeEnum = z.infer<typeof TransactionEventTypeEnum>;

export enum TransactionEventProtocol {
  COMPOUND = 'compound',
  GAS = 'gas',
  GITCOIN = 'gitcoin',
  MAKERDAO = 'makerdao',
  UNISWAP = 'uniswap',
  AAVE = 'aave',
  XDAI = 'xdai',
  FRAX = 'frax',
  CONVEX = 'convex',
  ZKSYNC = 'zksync',
  '1INCH' = '1inch',
  VOTIUM = 'votium',
  LIQUITY = 'liquity',
  PICKLE = 'pickle finance',
  DXDAO = 'dxdao',
  BADGER = 'badger',
  ENS = 'ens',
  CURVE = 'curve',
  KRAKEN = 'kraken',
  SHAPESHIFT = 'shapeshift',
  ELEMENT_FINANCE = 'element-finance',
  HOP_PROTOCOL = 'hop-protocol',
  SUSHISWAP = 'sushiswap',
  WETH = 'weth'
}
