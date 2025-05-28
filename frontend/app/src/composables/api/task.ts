import type { ActionResult } from '@rotki/common';
import type { AxiosRequestConfig, AxiosResponseTransformer } from 'axios';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validTaskStatus } from '@/services/utils';
import { withRetry } from '@/services/with-retry';
import { ApiValidationError } from '@/types/api/errors';
import { IncompleteUpgradeError, SyncConflictError, SyncConflictPayload } from '@/types/login';
import { TaskNotFoundError, type TaskResultResponse, type TaskStatus } from '@/types/task';
import { isEmpty } from 'es-toolkit/compat';

interface UseTaskApiReturn {
  queryTasks: () => Promise<TaskStatus>;
  queryTaskResult: <T>(id: number, transformer?: AxiosResponseTransformer[]) => Promise<ActionResult<T>>;
  cancelAsyncTask: (id: number) => Promise<boolean>;
}

export function useTaskApi(): UseTaskApiReturn {
  const queryTasks = async (): Promise<TaskStatus> => withRetry(async () => {
    const response = await api.instance.get<ActionResult<TaskStatus>>(`/tasks`, {
      validateStatus: validTaskStatus,
    });

    return handleResponse(response);
  });

  const queryTaskResult = async <T>(
    id: number,
    transformer?: AxiosResponseTransformer[],
  ): Promise<ActionResult<T>> => {
    const config: Partial<AxiosRequestConfig> = {
      timeout: 90_000,
      validateStatus: validTaskStatus,
    };

    if (transformer)
      config.transformResponse = transformer;

    const response = await api.instance.get<ActionResult<TaskResultResponse<ActionResult<T>>>>(`/tasks/${id}`, config);

    if (response.status === 404)
      throw new TaskNotFoundError(`Task with id ${id} not found`);

    const { outcome, statusCode } = handleResponse(response);

    if (outcome) {
      const { message, result } = outcome;

      if (statusCode === 300) {
        if (typeof result === 'object') {
          if (isEmpty(result))
            throw new IncompleteUpgradeError(message);

          throw new SyncConflictError(message, SyncConflictPayload.parse(result));
        }
      }
      else if (statusCode === 400) {
        throw new ApiValidationError(message);
      }
      else if (statusCode === 502) {
        throw new Error(message);
      }
      return outcome;
    }

    throw new Error('No result');
  };

  const cancelAsyncTask = async (id: number): Promise<boolean> => {
    const config: Partial<AxiosRequestConfig> = {
      validateStatus: validTaskStatus,
    };

    const response = await api.instance.delete<ActionResult<boolean>>(`/tasks/${id}`, config);

    if (response.status === 404)
      throw new TaskNotFoundError(`Task with id ${id} not found`);

    return handleResponse(response);
  };

  return {
    cancelAsyncTask,
    queryTaskResult,
    queryTasks,
  };
}
