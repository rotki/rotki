import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiValidationError } from '@/types/api/errors';
import { IncompleteUpgradeError, SyncConflictError } from '@/types/login';
import { TaskNotFoundError } from '@/types/task';
import { useTaskApi } from './task';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/task', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryTasks', () => {
    it('fetches list of pending and completed tasks', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks`, () =>
          HttpResponse.json({
            result: {
              pending: [1, 2, 3],
              completed: [4, 5],
            },
            message: '',
          })),
      );

      const { queryTasks } = useTaskApi();
      const result = await queryTasks();

      expect(result.pending).toEqual([1, 2, 3]);
      expect(result.completed).toEqual([4, 5]);
    });

    it('handles empty task lists', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks`, () =>
          HttpResponse.json({
            result: {
              pending: [],
              completed: [],
            },
            message: '',
          })),
      );

      const { queryTasks } = useTaskApi();
      const result = await queryTasks();

      expect(result.pending).toEqual([]);
      expect(result.completed).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to query tasks',
          })),
      );

      const { queryTasks } = useTaskApi();

      await expect(queryTasks())
        .rejects
        .toThrow('Failed to query tasks');
    });
  });

  describe('queryTaskResult', () => {
    it('fetches completed task result', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: {
              outcome: {
                result: { data: 'test-data' },
                message: '',
              },
              status: 'completed',
            },
            message: '',
          })),
      );

      const { queryTaskResult } = useTaskApi();
      const result = await queryTaskResult<{ data: string }>(123);

      expect(result.result).toEqual({ data: 'test-data' });
      expect(result.message).toBe('');
    });

    it('throws TaskNotFoundError on 404', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks/999`, () =>
          HttpResponse.json(
            {
              result: null,
              message: 'Task not found',
            },
            { status: 404 },
          )),
      );

      const { queryTaskResult } = useTaskApi();

      await expect(queryTaskResult(999))
        .rejects
        .toThrow(TaskNotFoundError);
    });

    it('throws IncompleteUpgradeError on statusCode 300 with empty result', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: {
              outcome: {
                result: {},
                message: 'Upgrade incomplete',
              },
              status: 'completed',
              statusCode: 300,
            },
            message: '',
          })),
      );

      const { queryTaskResult } = useTaskApi();

      await expect(queryTaskResult(123))
        .rejects
        .toThrow(IncompleteUpgradeError);
    });

    it('throws SyncConflictError on statusCode 300 with conflict data', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: {
              outcome: {
                result: {
                  local_last_modified: 1700000000,
                  remote_last_modified: 1700100000,
                },
                message: 'Sync conflict detected',
              },
              status: 'completed',
              statusCode: 300,
            },
            message: '',
          })),
      );

      const { queryTaskResult } = useTaskApi();

      await expect(queryTaskResult(123))
        .rejects
        .toThrow(SyncConflictError);
    });

    it('throws ApiValidationError on statusCode 400', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: {
              outcome: {
                result: null,
                message: 'Validation failed',
              },
              status: 'completed',
              statusCode: 400,
            },
            message: '',
          })),
      );

      const { queryTaskResult } = useTaskApi();

      await expect(queryTaskResult(123))
        .rejects
        .toThrow(ApiValidationError);
    });

    it('throws error on statusCode 502', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: {
              outcome: {
                result: null,
                message: 'Backend unavailable',
              },
              status: 'completed',
              statusCode: 502,
            },
            message: '',
          })),
      );

      const { queryTaskResult } = useTaskApi();

      await expect(queryTaskResult(123))
        .rejects
        .toThrow('Backend unavailable');
    });

    it('throws error when no outcome', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: {
              outcome: null,
              status: 'pending',
            },
            message: '',
          })),
      );

      const { queryTaskResult } = useTaskApi();

      await expect(queryTaskResult(123))
        .rejects
        .toThrow('No result');
    });
  });

  describe('cancelAsyncTask', () => {
    it('cancels a task successfully', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
      );

      const { cancelAsyncTask } = useTaskApi();
      const result = await cancelAsyncTask(123);

      expect(result).toBe(true);
    });

    it('throws TaskNotFoundError on 404', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/tasks/999`, () =>
          HttpResponse.json(
            {
              result: null,
              message: 'Task not found',
            },
            { status: 404 },
          )),
      );

      const { cancelAsyncTask } = useTaskApi();

      await expect(cancelAsyncTask(999))
        .rejects
        .toThrow(TaskNotFoundError);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/tasks/123`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to cancel task',
          })),
      );

      const { cancelAsyncTask } = useTaskApi();

      await expect(cancelAsyncTask(123))
        .rejects
        .toThrow('Failed to cancel task');
    });
  });
});
