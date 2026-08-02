import type { ActivityKind } from '@/modules/task-center/core/types';

/** The two kinds of work the balance-query indicator distinguishes. */
export type BalanceQueryProgressType = typeof ActivityKind.TOKEN_DETECTION | typeof ActivityKind.BLOCKCHAIN_BALANCES;

export interface BalanceQueryQueueItem {
  id: string;
  type: BalanceQueryProgressType;
  chain: string;
  address?: string;
  status: 'pending' | 'running' | 'completed';
  addedAt: number;
}

export interface CommonQueryProgressData<T> {
  currentStep: number;
  totalSteps: number;
  percentage: number;
  currentOperation: string | null;
  currentOperationData: T | null;
}

export type HistoryQueryProgressType = 'transaction' | 'event';
