import { balanceKeys } from '@/services/consts';

export const DEFI_EVENT_REPAY = 'repay';
export const DEFI_EVENT_LIQUIDATION = 'liquidation';
export const DEFI_EVENT_BORROW = 'borrow';

export const COMPOUND_EVENT_TYPES = [
  'mint',
  'redeem',
  DEFI_EVENT_BORROW,
  DEFI_EVENT_REPAY,
  DEFI_EVENT_LIQUIDATION,
  'comp'
] as const;

export const dsrKeys = [...balanceKeys, 'current_dsr'];
export const vaultDetailsKeys = [...balanceKeys, 'total_interest_owed'];
export const vaultKeys = [...balanceKeys, 'liquidation_price'];
export const aaveHistoryKeys = [
  ...balanceKeys,
  'accrued_borrow_interest',
  'borrow_rate'
];

export enum ProtocolVersion {
  V1 = 'v1',
  V2 = 'v2'
}
