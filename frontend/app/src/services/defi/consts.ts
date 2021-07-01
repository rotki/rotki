import { balanceKeys } from '@/services/consts';

export const DEFI_YEARN_VAULTS = 'yearn_vaults';
export const DEFI_YEARN_VAULTS_V2 = 'yearn_vaults_v2';
export const DEFI_AAVE = 'aave';
export const DEFI_MAKERDAO = 'makerdao';
export const DEFI_COMPOUND = 'compound';
export const DEFI_UNISWAP = 'uniswap';

export const DEFI_PROTOCOLS = [
  DEFI_AAVE,
  DEFI_MAKERDAO,
  DEFI_COMPOUND,
  DEFI_YEARN_VAULTS,
  DEFI_YEARN_VAULTS_V2,
  DEFI_UNISWAP
] as const;

export const DEFI_EVENT_REPAY = 'repay';
export const DEFI_EVENT_LIQUIDATION = 'liquidation';
export const DEFI_EVENT_BORROW = 'borrow';

export const DEFI_EVENT_DEPOSIT = 'deposit';
export const DEFI_EVENT_INTEREST = 'interest';
export const DEFI_EVENT_WITHDRAWAL = 'withdrawal';

export const COMPOUND_EVENT_TYPES = [
  'mint',
  'redeem',
  DEFI_EVENT_BORROW,
  DEFI_EVENT_REPAY,
  DEFI_EVENT_LIQUIDATION,
  'comp'
] as const;

export const AAVE_BORROWING_EVENTS = [
  DEFI_EVENT_BORROW,
  DEFI_EVENT_REPAY,
  DEFI_EVENT_LIQUIDATION
] as const;

export const AAVE_LENDING_EVENTS = [
  DEFI_EVENT_DEPOSIT,
  DEFI_EVENT_INTEREST,
  DEFI_EVENT_WITHDRAWAL
] as const;

export const dsrKeys = [...balanceKeys, 'current_dsr'];
export const vaultDetailsKeys = [...balanceKeys, 'total_interest_owed'];
export const vaultKeys = [...balanceKeys, 'liquidation_price'];
export const aaveHistoryKeys = [
  ...balanceKeys,
  'accrued_borrow_interest',
  'borrow_rate'
];

export const V1 = 'v1' as const;
export const V2 = 'v2' as const;

export const PROTOCOL_VERSION = [V1, V2] as const;
