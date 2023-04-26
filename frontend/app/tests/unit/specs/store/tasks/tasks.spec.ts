import { type ActionResult } from '@rotki/common/lib/data';
import { rest } from 'msw';
import { expect } from 'vitest';
import { api } from '@/services/rotkehlchen-api';
import {
  BackendCancelledTaskError,
  type TaskMeta,
  type TaskResultResponse,
  type TaskStatus
} from '@/types/task';
import { TaskType } from '@/types/task-type';
import { server } from '../../../setup-files/server';
import createPinia from '../../../utils/create-pinia';

const backendUrl = process.env.VITE_BACKEND_URL;

const getResult = <T>(t: T, message?: string): ActionResult<T> => ({
  result: t,
  message: message ?? ''
});

const getTaskResult = <T>(
  id: number,
  data: T,
  options?: {
    requestStatus?: number;
    taskResultStatus?: 'completed' | 'not-found' | 'pending';
    taskResultMessage?: string;
    taskResultStatusCode?: number;
  }
) => ({
  id,
  status: options?.requestStatus ?? 200,
  body: {
    outcome: getResult(data, options?.taskResultMessage),
    status: options?.taskResultStatus ?? 'completed',
    statusCode: options?.taskResultStatusCode ?? 200
  } satisfies TaskResultResponse<ActionResult<T>>
});

const mockTasks = (data: {
  status: TaskStatus;
  tasks: {
    id: number;
    status: number;
    body: TaskResultResponse<ActionResult<any>>;
  }[];
}) => [
  rest.get(`${backendUrl}/api/1/tasks`, (req, res, ctx) =>
    res(ctx.status(200), ctx.json(getResult(data.status)))
  ),
  ...data.tasks.map(task =>
    rest.get(`${backendUrl}/api/1/tasks/${task.id}`, (req, res, ctx) =>
      res(ctx.status(task.status), ctx.json(getResult(task.body)))
    )
  )
];

const getMeta = (opts?: Partial<TaskMeta>): TaskMeta => ({
  title: '',
  ...opts
});

describe('store:tasks', () => {
  let store: ReturnType<typeof useTaskStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useTaskStore();
    server.resetHandlers();
  });

  test('task is not running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    expect(get(store.isTaskRunning(TaskType.IMPORT_CSV))).toBe(false);
  });

  test('task is running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    expect(get(store.isTaskRunning(TaskType.MANUAL_BALANCES_ADD))).toBe(true);
  });

  test('task is running with strict meta check', () => {
    const meta = getMeta({
      title: 'test',
      description: 'test'
    });
    store.addTask(1, TaskType.TX, meta);
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    expect(get(store.isTaskRunning(TaskType.TX, getMeta()))).toBe(false);
    expect(get(store.isTaskRunning(TaskType.TX, meta))).toBe(true);
  });

  test('unknown tasks do not have metadata', () => {
    expect(store.metadata(TaskType.ADD_ACCOUNT)).toBeUndefined();
  });

  test('monitoring removes ignored tasks', async () => {
    store.addTask(1, TaskType.QUERY_BALANCES, getMeta({ ignoreResult: true }));
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: []
        },
        tasks: [getTaskResult(1, true)]
      })
    );

    expect(get(store.isTaskRunning(TaskType.QUERY_BALANCES))).toBe(true);
    expect(get(store.metadata(TaskType.QUERY_BALANCES))).toMatchObject({
      title: '',
      ignoreResult: true
    });

    await store.monitor();

    expect(get(store.isTaskRunning(TaskType.QUERY_BALANCES))).toBe(false);
  });

  test('monitoring resolves an awaited task', async () => {
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: []
        },
        tasks: [getTaskResult(1, true)]
      })
    );

    const [response] = await Promise.all([
      store.awaitTask<boolean, TaskMeta>(1, TaskType.IMPORT_CSV, getMeta()),
      store.monitor()
    ]);

    expect(response.result).toBe(true);
  });

  test('monitor consumes an unknown task', async () => {
    server.use(
      ...mockTasks({
        status: {
          completed: [1, 2],
          pending: []
        },
        tasks: [getTaskResult(1, true), getTaskResult(2, true)]
      })
    );

    const get = vi.spyOn(api.instance, 'get');

    const [response] = await Promise.all([
      store.awaitTask<boolean, TaskMeta>(2, TaskType.IMPORT_CSV, getMeta()),
      store.monitor()
    ]);

    expect(response.result).toBe(true);
    expect(get).toHaveBeenCalledTimes(3);
    expect(get).toHaveBeenCalledWith('/tasks/1', expect.anything());
  });

  test('monitor awaits non-unique tasks', async () => {
    server.use(
      ...mockTasks({
        status: {
          completed: [1, 2],
          pending: []
        },
        tasks: [getTaskResult(1, 1), getTaskResult(2, 2)]
      })
    );

    const [response, response2] = await Promise.all([
      store.awaitTask<number, TaskMeta>(
        1,
        TaskType.IMPORT_CSV,
        getMeta(),
        true
      ),
      store.awaitTask<number, TaskMeta>(
        2,
        TaskType.IMPORT_CSV,
        getMeta(),
        true
      ),
      store.monitor()
    ]);

    expect(response.result).toBe(1);
    expect(response2.result).toBe(2);
  });

  test('null result raises an error', async () => {
    expect.assertions(1);
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: []
        },
        tasks: [
          getTaskResult(1, null, {
            taskResultMessage: 'failed'
          })
        ]
      })
    );

    await expect(
      Promise.all([
        store.awaitTask<number, TaskMeta>(
          1,
          TaskType.IMPORT_CSV,
          getMeta(),
          true
        ),
        store.monitor()
      ])
    ).rejects.toThrow(new Error('failed'));
  });

  test('empty message and null result raises a backend cancelled error', async () => {
    expect.assertions(1);
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: []
        },
        tasks: [getTaskResult(1, null)]
      })
    );

    await expect(
      Promise.all([
        store.awaitTask<number, TaskMeta>(
          1,
          TaskType.IMPORT_CSV,
          getMeta(),
          true
        ),
        store.monitor()
      ])
    ).rejects.toThrow(
      new BackendCancelledTaskError(
        'Backend cancelled task_id: 1, task_type: IMPORT_CSV'
      )
    );
  });

  test('not found tasks result into an error', async () => {
    expect.assertions(1);
    server.use(
      ...mockTasks({
        status: {
          completed: [1],
          pending: []
        },
        tasks: [
          getTaskResult(1, null, {
            requestStatus: 404
          })
        ]
      })
    );

    const [response] = await Promise.all([
      store.awaitTask<number, TaskMeta>(
        1,
        TaskType.IMPORT_CSV,
        getMeta(),
        true
      ),
      store.monitor()
    ]);

    expect(response.message).toContain('Task with id 1 not found');
  });
});
