import { balanceKeys } from '@/services/consts';

export const DEFI_YEARN_VAULTS = 'yearn_vaults';
export const DEFI_AAVE = 'aave';
export const DEFI_MAKERDAO = 'makerdao';
export const DEFI_COMPOUND = 'compound';

export const DEFI_PROTOCOLS = [
  DEFI_AAVE,
  DEFI_MAKERDAO,
  DEFI_COMPOUND,
  DEFI_YEARN_VAULTS
] as const;
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
