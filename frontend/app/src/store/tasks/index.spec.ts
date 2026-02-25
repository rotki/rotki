import type { ActionResult } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { createCustomPinia } from '@test/utils/create-pinia';
import { http, type HttpHandler, HttpResponse, type StrictResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTaskStore } from '@/store/tasks';
import { BackendCancelledTaskError, type TaskMeta, type TaskResultResponse, type TaskStatus } from '@/types/task';
import { TaskType } from '@/types/task-type';

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
): { id: number; status: number; body: TaskResultResponse<ActionResult<T>> } {
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
}): HttpHandler[] {
  return [
    http.get(`${backendUrl}/api/1/tasks`, (): StrictResponse<ActionResult<TaskStatus>> => HttpResponse.json(getResult(data.status), { status: 200 })),
    ...data.tasks.map((task): HttpHandler =>
      http.get(`${backendUrl}/api/1/tasks/${task.id}`, (): StrictResponse<ActionResult<TaskResultResponse<ActionResult<any>>>> =>
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

describe('useTaskStore', () => {
  let store: ReturnType<typeof useTaskStore>;

  beforeEach((): void => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    store = useTaskStore();
    server.resetHandlers();
    vi.clearAllMocks();
  });

  it('should report task as not running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    expect(get(store.useIsTaskRunning(TaskType.IMPORT_CSV))).toBe(false);
  });

  it('should report task as running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    expect(get(store.useIsTaskRunning(TaskType.MANUAL_BALANCES_ADD))).toBe(true);
  });

  it('should report task as running with strict meta check', () => {
    const meta = getMeta({
      title: 'test',
      description: 'test',
    });
    store.addTask(1, TaskType.TX, meta);
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    expect(get(store.useIsTaskRunning(TaskType.TX, getMeta()))).toBe(false);
    expect(get(store.useIsTaskRunning(TaskType.TX, meta))).toBe(true);
  });

  it('should not have metadata for unknown tasks', () => {
    expect(store.metadata(TaskType.ADD_ACCOUNT)).toBeUndefined();
  });

  it('should remove ignored tasks during monitoring', async () => {
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

  it('should resolve an awaited task during monitoring', async () => {
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

  it('should consume an unknown task during monitoring', async () => {
    vi.useFakeTimers();
    const requestedUrls: string[] = [];

    server.use(
      http.get(`${backendUrl}/api/1/tasks`, (): StrictResponse<any> => HttpResponse.json(getResult({ completed: [1, 2], pending: [] }), { status: 200 })),
      http.get(`${backendUrl}/api/1/tasks/:id`, ({ request, params }): StrictResponse<any> => {
        requestedUrls.push(new URL(request.url).pathname);
        const id = Number(params.id);
        return HttpResponse.json(getResult(getTaskResult(id, true).body), { status: 200 });
      }),
    );

    const [response] = await Promise.all([
      store.awaitTask<boolean, TaskMeta>(2, TaskType.IMPORT_CSV, getMeta()),
      store.monitor(),
    ]);

    await vi.advanceTimersByTimeAsync(31000);
    await store.monitor();

    expect(response.result).toBe(true);
    expect(requestedUrls).toContain('/api/1/tasks/1');
    expect(requestedUrls).toContain('/api/1/tasks/2');
    vi.useRealTimers();
  });

  it('should handle race condition delay', async () => {
    vi.useFakeTimers();
    const requestedUrls: string[] = [];

    server.use(
      http.get(`${backendUrl}/api/1/tasks`, (): StrictResponse<any> => HttpResponse.json(getResult({ completed: [1, 2], pending: [] }), { status: 200 })),
      http.get(`${backendUrl}/api/1/tasks/:id`, ({ request, params }): StrictResponse<any> => {
        requestedUrls.push(new URL(request.url).pathname);
        const id = Number(params.id);
        return HttpResponse.json(getResult(getTaskResult(id, true).body), { status: 200 });
      }),
    );

    await Promise.all([store.awaitTask<boolean, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta()), store.monitor()]);
    await vi.advanceTimersByTimeAsync(10000);
    const [response] = await Promise.all([
      store.awaitTask<boolean, TaskMeta>(2, TaskType.TX, getMeta()),
      store.monitor(),
    ]);

    expect(response.result).toBe(true);
    expect(requestedUrls).toContain('/api/1/tasks/1');
    expect(requestedUrls).toContain('/api/1/tasks/2');
    vi.useRealTimers();
  });

  it('should await non-unique tasks during monitoring', async () => {
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

  it('should raise an error on null result', async () => {
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

  it('should raise backend cancelled error on empty message and null result', async () => {
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

  it('should return error for not found tasks', async () => {
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
