import type { TaskType } from '@/types/task-type';

export type BalanceQueryProgressType = TaskType.FETCH_DETECTED_TOKENS | TaskType.QUERY_BLOCKCHAIN_BALANCES;

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
