import type { AxiosResponseTransformer } from 'axios';
import type { TaskType } from '@/types/task-type';

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
  readonly transformer?: AxiosResponseTransformer[];
}

export interface ExchangeMeta extends TaskMeta {
  readonly location: string;
}

export interface BlockchainMetadata extends TaskMeta {
  readonly blockchain?: string;
}

export interface TaskResultResponse<T> {
  outcome: T | null;
  status: 'completed' | 'not-found' | 'pending';
  statusCode?: number;
}

export interface TaskStatus {
  readonly pending: number[];
  readonly completed: number[];
}

export type TaskMap<T extends TaskMeta> = Record<number, Task<T>>;

export class TaskNotFoundError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = 'TaskNotFoundError';
  }
}

export class BackendCancelledTaskError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = 'BackendCancelledTaskError';
  }
}

export class UserCancelledTaskError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = 'UserCancelledTaskError';
  }
}

export interface PendingTask {
  readonly taskId: number;
}
