import type { PaginationRequestPayload } from '@/modules/common/common-types';

export const InternalTxConflictActions = {
  FIX_REDECODE: 'fix_redecode',
  REPULL: 'repull',
} as const;

export type InternalTxConflictAction = typeof InternalTxConflictActions[keyof typeof InternalTxConflictActions];

export const RepullReasons = {
  ALL_ZERO_GAS: 'all_zero_gas',
  OTHER: 'other',
} as const;

export type RepullReason = typeof RepullReasons[keyof typeof RepullReasons];

export const RedecodeReasons = {
  DUPLICATE_EXACT_ROWS: 'duplicate_exact_rows',
  MIXED_ZERO_GAS: 'mixed_zero_gas',
  MIXED_ZERO_GAS_AND_DUPLICATE: 'mixed_zero_gas_and_duplicate',
} as const;

export type RedecodeReason = typeof RedecodeReasons[keyof typeof RedecodeReasons];

export const InternalTxConflictStatuses = {
  FAILED: 'failed',
  FIXED: 'fixed',
  PENDING: 'pending',
} as const;

export type InternalTxConflictStatus = typeof InternalTxConflictStatuses[keyof typeof InternalTxConflictStatuses];

export interface InternalTxConflict {
  chain: string;
  txHash: string;
  groupIdentifier: string | null;
  timestamp: number | null;
  action: InternalTxConflictAction;
  repullReason: RepullReason | null;
  redecodeReason: RedecodeReason | null;
  lastRetryTs: number | null;
  lastError: string | null;
}

export interface InternalTxConflictsRequestPayload extends PaginationRequestPayload<InternalTxConflict> {
  txHash?: string;
  chain?: string;
  fixed?: boolean;
  failed?: boolean;
  fromTimestamp?: number;
  toTimestamp?: number;
}

export interface InternalTxConflictsCountResponse {
  pending: number;
  failed: number;
}
