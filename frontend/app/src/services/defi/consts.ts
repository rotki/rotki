import { balanceKeys } from '@/services/consts';

export const aaveHistoryKeys = [
  ...balanceKeys,
  'accrued_borrow_interest',
  'borrow_rate'
];

export enum ProtocolVersion {
  V1 = 'v1',
  V2 = 'v2'
}
