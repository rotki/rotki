import type { ActionResult } from '@rotki/common';
import { isEmpty } from 'es-toolkit/compat';
import { ofetch } from 'ofetch';
import { DEFAULT_TIMEOUT, TASKS_TIMEOUT } from '@/modules/api/constants';
import { api } from '@/modules/api/rotki-api';
import { camelCaseTransformer } from '@/modules/api/transformers';
import { VALID_TASK_STATUS } from '@/modules/api/utils';
import { ApiValidationError } from '@/types/api/errors';
import { HTTPStatus } from '@/types/api/http';
import { IncompleteUpgradeError, SyncConflictError, SyncConflictPayload } from '@/types/login';
import { TaskNotFoundError, type TaskResultResponse, type TaskStatus } from '@/types/task';

interface UseTaskApiReturn {
  queryTasks: () => Promise<TaskStatus>;
  queryTaskResult: <T>(id: number) => Promise<ActionResult<T>>;
  cancelAsyncTask: (id: number) => Promise<boolean>;
}

export function useTaskApi(): UseTaskApiReturn {
  const queryTasks = async (): Promise<TaskStatus> => api.get<TaskStatus>('/tasks', {
    timeout: TASKS_TIMEOUT,
    validStatuses: VALID_TASK_STATUS,
    retry: true,
  });

  /**
   * Fetches a task result by ID with specialized error handling for task-specific status codes.
   * Handles:
   * - 404: TaskNotFoundError
   * - 300 with empty result: IncompleteUpgradeError
   * - 300 with conflict data: SyncConflictError
   * - 400: ApiValidationError
   * - 502: Error with backend unavailable message
   */
  const queryTaskResult = async <T>(id: number): Promise<ActionResult<T>> => {
    const response = await ofetch.raw<ActionResult<TaskResultResponse<ActionResult<T>>>>(`/tasks/${id}`, {
      baseURL: api.baseURL,
      timeout: TASKS_TIMEOUT,
      ignoreResponseError: true,
      parseResponse: (text: string) => camelCaseTransformer(JSON.parse(text)),
    });

    const status = response.status;

    // Handle 404 - task not found
    if (status === HTTPStatus.NOT_FOUND)
      throw new TaskNotFoundError(`Task with id ${id} not found`);

    const data = response._data;

    if (!data?.result)
      throw new Error(data?.message || 'No result');

    const { outcome, statusCode } = data.result;

    if (outcome) {
      const { message, result } = outcome;

      // Handle special status codes from the backend
      if (statusCode === HTTPStatus.MULTIPLE_CHOICES) {
        if (typeof result === 'object') {
          if (isEmpty(result))
            throw new IncompleteUpgradeError(message);

          throw new SyncConflictError(message, SyncConflictPayload.parse(result));
        }
      }
      else if (statusCode === HTTPStatus.BAD_REQUEST) {
        throw new ApiValidationError(message);
      }
      else if (statusCode === HTTPStatus.BAD_GATEWAY) {
        throw new Error(message);
      }
      return outcome;
    }

    throw new Error('No result');
  };

  /**
   * Cancels an async task by ID.
   * @returns true if successfully cancelled
   * @throws TaskNotFoundError if task doesn't exist
   */
  const cancelAsyncTask = async (id: number): Promise<boolean> => {
    const response = await ofetch.raw<ActionResult<boolean>>(`/tasks/${id}`, {
      method: 'DELETE',
      baseURL: api.baseURL,
      timeout: DEFAULT_TIMEOUT,
      ignoreResponseError: true,
      parseResponse: (text: string) => camelCaseTransformer(JSON.parse(text)),
    });

    const status = response.status;

    // Handle 404 - task not found
    if (status === HTTPStatus.NOT_FOUND)
      throw new TaskNotFoundError(`Task with id ${id} not found`);

    const data = response._data;

    if (!data?.result)
      throw new Error(data?.message || 'Failed to cancel task');

    return data.result;
  };

  return {
    cancelAsyncTask,
    queryTaskResult,
    queryTasks,
  };
}
