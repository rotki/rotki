import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { useTaskStore } from '@/store/tasks';
import { BackendCancelledTaskError, type TaskMeta, type TaskResultResponse, type TaskStatus } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { server } from '../../../setup-files/server';
import { createCustomPinia } from '../../../utils/create-pinia';

const backendUrl = process.env.VITE_BACKEND_URL;

function getResult<T>(t: T, message?: string): ActionResult<T> {
  return {
    result: t,
    message: message ?? '',
  };
}

function getTaskResult<T>(
  id: number,
  data: T,
  options?: {
    requestStatus?: number;
    taskResultStatus?: 'completed' | 'not-found' | 'pending';
    taskResultMessage?: string;
    taskResultStatusCode?: number;
  },
) {
  return {
    id,
    status: options?.requestStatus ?? 200,
    body: {
      outcome: getResult(data, options?.taskResultMessage),
      status: options?.taskResultStatus ?? 'completed',
      statusCode: options?.taskResultStatusCode ?? 200,
    } satisfies TaskResultResponse<ActionResult<T>>,
  };
}

function mockTasks(data: {
  status: TaskStatus;
  tasks: {
    id: number;
    status: number;
    body: TaskResultResponse<ActionResult<any>>;
  }[];
}) {
  return [
    http.get(`${backendUrl}/api/1/tasks`, () => HttpResponse.json(getResult(data.status), { status: 200 })),
    ...data.tasks.map(task =>
      http.get(`${backendUrl}/api/1/tasks/${task.id}`, () =>
        HttpResponse.json(getResult(task.body), { status: task.status })),
    ),
  ];
}

function getMeta(opts?: Partial<TaskMeta>): TaskMeta {
  return {
    title: '',
    ...opts,
  };
}

describe('store:tasks', () => {
  let store: ReturnType<typeof useTaskStore>;

  beforeEach(() => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    store = useTaskStore();
    server.resetHandlers();
    vi.clearAllMocks();
  });

  it('task is not running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    expect(get(store.useIsTaskRunning(TaskType.IMPORT_CSV))).toBe(false);
  });

  it('task is running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    expect(get(store.useIsTaskRunning(TaskType.MANUAL_BALANCES_ADD))).toBe(true);
  });

  it('task is running with strict meta check', () => {
    const meta = getMeta({
      title: 'test',
      description: 'test',
    });
    store.addTask(1, TaskType.TX, meta);
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    expect(get(store.useIsTaskRunning(TaskType.TX, getMeta()))).toBe(false);
    expect(get(store.useIsTaskRunning(TaskType.TX, meta))).toBe(true);
  });

  it('unknown tasks do not have metadata', () => {
    expect(store.metadata(TaskType.ADD_ACCOUNT)).toBeUndefined();
  });

  it('monitoring removes ignored tasks', async () => {
    store.addTask(1, TaskType.QUERY_BALANCES, getMeta({ ignoreResult: true }));
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: [],
        },
        tasks: [getTaskResult(1, true)],
      }),
    );

    expect(get(store.useIsTaskRunning(TaskType.QUERY_BALANCES))).toBe(true);
    expect(get(store.metadata(TaskType.QUERY_BALANCES))).toMatchObject({
      title: '',
      ignoreResult: true,
    });

    await store.monitor();

    expect(get(store.useIsTaskRunning(TaskType.QUERY_BALANCES))).toBe(false);
  });

  it('monitoring resolves an awaited task', async () => {
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: [],
        },
        tasks: [getTaskResult(1, true)],
      }),
    );

    const [response] = await Promise.all([
      store.awaitTask<boolean, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta()),
      store.monitor(),
    ]);

    expect(response.result).toBe(true);
  });

  it('monitor consumes an unknown task', async () => {
    vi.useFakeTimers();
    server.use(
      ...mockTasks({
        status: {
          completed: [1, 2],
          pending: [],
        },
        tasks: [getTaskResult(1, true), getTaskResult(2, true)],
      }),
    );

    const get = vi.spyOn(api.instance, 'get');

    const [response] = await Promise.all([
      store.awaitTask<boolean, TaskMeta>(2, TaskType.IMPORT_CSV, getMeta()),
      store.monitor(),
    ]);

    await vi.advanceTimersByTimeAsync(31000);
    await store.monitor();

    expect(response.result).toBe(true);
    expect(get).toHaveBeenCalledTimes(4);
    expect(get).toHaveBeenCalledWith('/tasks/1', expect.anything());
    expect(get).toHaveBeenCalledWith('/tasks/2', expect.anything());
    vi.useRealTimers();
  });

  it('handles race condition delay', async () => {
    vi.useFakeTimers();
    server.use(
      ...mockTasks({
        status: {
          completed: [1, 2],
          pending: [],
        },
        tasks: [getTaskResult(1, true), getTaskResult(2, true)],
      }),
    );

    const get = vi.spyOn(api.instance, 'get');

    await Promise.all([store.awaitTask<boolean, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta()), store.monitor()]);
    await vi.advanceTimersByTimeAsync(10000);
    const [response] = await Promise.all([
      store.awaitTask<boolean, TaskMeta>(2, TaskType.TX, getMeta()),
      store.monitor(),
    ]);

    expect(response.result).toBe(true);
    expect(get).toHaveBeenCalledTimes(4);
    expect(get).toHaveBeenCalledWith('/tasks/1', expect.anything());
    expect(get).toHaveBeenCalledWith('/tasks/2', expect.anything());
    vi.useRealTimers();
  });

  it('monitor awaits non-unique tasks', async () => {
    server.use(
      ...mockTasks({
        status: {
          completed: [1, 2],
          pending: [],
        },
        tasks: [getTaskResult(1, 1), getTaskResult(2, 2)],
      }),
    );

    const [response, response2] = await Promise.all([
      store.awaitTask<number, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta(), true),
      store.awaitTask<number, TaskMeta>(2, TaskType.IMPORT_CSV, getMeta(), true),
      store.monitor(),
    ]);

    expect(response.result).toBe(1);
    expect(response2.result).toBe(2);
  });

  it('null result raises an error', async () => {
    expect.assertions(1);
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: [],
        },
        tasks: [
          getTaskResult(1, null, {
            taskResultMessage: 'failed',
          }),
        ],
      }),
    );

    await expect(
      Promise.all([store.awaitTask<number, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta(), true), store.monitor()]),
    ).rejects.toThrow(new Error('failed'));
  });

  it('empty message and null result raises a backend cancelled error', async () => {
    expect.assertions(1);
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: [],
        },
        tasks: [getTaskResult(1, null)],
      }),
    );

    await expect(
      Promise.all([store.awaitTask<number, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta(), true), store.monitor()]),
    ).rejects.toThrow(new BackendCancelledTaskError('Backend cancelled task_id: 1, task_type: IMPORT_CSV'));
  });

  it('not found tasks result into an error', async () => {
    expect.assertions(1);
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: [],
        },
        tasks: [
          getTaskResult(1, null, {
            requestStatus: 404,
          }),
        ],
      }),
    );

    const [response] = await Promise.all([
      store.awaitTask<number, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta(), true),
      store.monitor(),
    ]);

    expect(response.message).toContain('Task with id 1 not found');
  });
});
