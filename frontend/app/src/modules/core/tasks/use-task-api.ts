import type { ActionResult } from '@rotki/common';
import { isEmpty } from 'es-toolkit/compat';
import { ofetch } from 'ofetch';
import { IncompleteUpgradeError, SyncConflictError, SyncConflictPayload } from '@/modules/auth/login';
import { CHAIN_KEYED_SETTINGS, DEFAULT_TIMEOUT, TASKS_TIMEOUT } from '@/modules/core/api/constants';
import { api } from '@/modules/core/api/rotki-api';
import { camelCaseTransformer } from '@/modules/core/api/transformers';
import { ApiKeyMissingError, ApiValidationError } from '@/modules/core/api/types/errors';
import { HTTPStatus } from '@/modules/core/api/types/http';
import { VALID_TASK_STATUS } from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema, TaskNotFoundError, type TaskResultResponse, type TaskStatus } from '@/modules/core/tasks/types';

type TriggerTaskType = 'historical_balance_processing' | 'asset_movement_matching' | 'bridge_matching';

interface SchedulerStateResponse {
  enabled: boolean;
}

interface UseTaskApiReturn {
  queryTasks: () => Promise<TaskStatus>;
  queryTaskResult: <T>(id: number) => Promise<ActionResult<T>>;
  cancelAsyncTask: (id: number) => Promise<boolean>;
  triggerTask: (task: TriggerTaskType) => Promise<PendingTask>;
  setSchedulerState: (enabled: boolean) => Promise<SchedulerStateResponse>;
}

/**
 * Translates the status code the backend reports inside a task outcome into the matching error.
 *
 * A 300 with a non-object result is deliberately not an error: the caller then treats the outcome as a
 * normal result, which is the behaviour the nested checks here preserve.
 */
function raiseForOutcomeStatus<T>(statusCode: number | undefined, outcome: ActionResult<T>): void {
  const { message, result } = outcome;

  if (statusCode === HTTPStatus.MULTIPLE_CHOICES) {
    if (typeof result !== 'object')
      return;

    if (isEmpty(result))
      throw new IncompleteUpgradeError(message);

    throw new SyncConflictError(message, { payload: SyncConflictPayload.parse(result) });
  }

  if (statusCode === HTTPStatus.BAD_REQUEST)
    throw new ApiValidationError(message);

  if (statusCode === HTTPStatus.FAILED_DEPENDENCY)
    throw new ApiKeyMissingError(message);

  if (statusCode === HTTPStatus.BAD_GATEWAY)
    throw new Error(message);
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
      // Declared here rather than on a request: login and account creation return the user's
      // settings as a task result, and this is the one fetch every task result comes through, so
      // there is no settings request to hang the exemption on. The named fields always carry a
      // chain-keyed map, whichever task they arrive in.
      parseResponse: (text: string) => camelCaseTransformer(JSON.parse(text), CHAIN_KEYED_SETTINGS),
    });

    const status = response.status;

    // Handle 404 - task not found
    if (status === HTTPStatus.NOT_FOUND)
      throw new TaskNotFoundError(`Task with id ${id} not found`);

    const data = response._data;

    if (!data?.result)
      throw new Error(data?.message ?? 'No result');

    const { outcome, statusCode } = data.result;

    if (outcome) {
      raiseForOutcomeStatus(statusCode, outcome);
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
      throw new Error(data?.message ?? 'Failed to cancel task');

    return data.result;
  };

  /**
   * Triggers a specific task type.
   * @param task - The type of task to trigger
   * @returns PendingTask with task ID
   */
  const triggerTask = async (task: TriggerTaskType): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/tasks/trigger', {
      asyncQuery: true,
      task,
    });
    return PendingTaskSchema.parse(response);
  };

  /**
   * Enables or disables the periodic task scheduler.
   * Should be called once initial data loading is complete.
   * @param enabled - Whether to enable the scheduler
   * @returns The new scheduler state
   */
  const setSchedulerState = async (enabled: boolean): Promise<SchedulerStateResponse> =>
    api.put<SchedulerStateResponse>('/tasks/scheduler', { enabled });

  return {
    cancelAsyncTask,
    queryTaskResult,
    queryTasks,
    setSchedulerState,
    triggerTask,
  };
}
