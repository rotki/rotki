import { TaskType } from '@/model/task-type';
import { taskManager } from '@/services/task-manager';
import { Blockchain } from '@/typing/types';

export interface Task<T extends TaskMeta> {
  readonly id: number;
  readonly type: TaskType;
  readonly meta: T;
}

export interface TaskMeta {
  readonly title: string;
  readonly description?: string;
  readonly ignoreResult: boolean;
  readonly numericKeys?: string[];
}

export interface ExchangeMeta extends TaskMeta {
  readonly name: string;
}

export interface BlockchainMetadata extends TaskMeta {
  readonly blockchain?: Blockchain;
}

export const createTask: <T extends TaskMeta>(
  id: number,
  type: TaskType,
  meta: T
) => Task<T> = (id, type, meta) => ({
  id,
  type,
  meta
});

export function taskCompletion<R, M extends TaskMeta>(
  task: TaskType,
  taskId?: string
): Promise<TaskResult<R, M>> {
  return new Promise((resolve, reject) => {
    taskManager.registerHandler<R, M>(
      task,
      (actionResult, meta) => {
        taskManager.unregisterHandler(task, taskId);
        const { result, message } = actionResult;
        if (message) {
          reject(new Error(message));
        } else {
          resolve({ result, meta });
        }
      },
      taskId
    );
  });
}

export interface TaskResult<R, M extends TaskMeta> {
  readonly result: R;
  readonly meta: M;
}
