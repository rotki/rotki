import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';

export interface Task<T extends TaskMeta> {
  readonly id: number;
  readonly type: TaskType;
  readonly meta: T;
  readonly time: number;
}

export interface TaskMeta {
  readonly title: string;
  readonly description?: string;
  readonly ignoreResult?: boolean;
  readonly numericKeys?: string[] | null;
}

export interface ExchangeMeta extends TaskMeta {
  readonly location: string;
}

export interface BlockchainMetadata extends TaskMeta {
  readonly blockchain?: Blockchain;
}

export interface AddressMeta extends TaskMeta {
  readonly address: string;
}

export interface TaskResultResponse<T> {
  outcome: T | null;
  status: 'completed' | 'not-found' | 'pending';
}
