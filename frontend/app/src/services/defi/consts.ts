import { balanceKeys } from '@/services/consts';

export const DEFI_PROTOCOLS = ['aave', 'makerdao', 'compound'] as const;
export const COMPOUND_EVENT_TYPES = [
  'mint',
  'redeem',
  'borrow',
  'repay',
  'liquidation',
  'comp'
] as const;

export const dsrKeys = [...balanceKeys, 'current_dsr'];
export const vaultDetailsKeys = [...balanceKeys, 'total_interest_owed'];
export const vaultKeys = [...balanceKeys, 'liquidation_price'];
