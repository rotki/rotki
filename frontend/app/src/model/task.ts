import { Blockchain } from '@rotki/common/lib/blockchain';
import dayjs from 'dayjs';
import { TaskType } from '@/model/task-type';
import { taskManager } from '@/services/task-manager';
import { assert } from '@/utils/assertions';

export interface Task<T extends TaskMeta> {
  readonly id: number;
  readonly type: TaskType;
  readonly meta: T;
  readonly time: number;
}

export interface TaskMeta {
  readonly title: string;
  readonly description?: string;
  readonly ignoreResult: boolean;
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

export const createTask: <T extends TaskMeta>(
  id: number,
  type: TaskType,
  meta: T
) => Task<T> = (id, type, meta) => {
  assert(
    !(id === null || id === undefined),
    `missing id for ${TaskType[type]} with ${JSON.stringify(meta)}`
  );
  return {
    id,
    type,
    meta,
    time: dayjs().valueOf()
  };
};

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
        if (message && result === null) {
          reject(new Error(message));
        } else {
          resolve({ result, meta });
        }
      },
      taskId
    );
  });
}

interface TaskResult<R, M extends TaskMeta> {
  readonly result: R;
  readonly meta: M;
}
