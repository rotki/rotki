import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSyncApi } from './use-sync-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/session/sync', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('forceSync', () => {
    it('should send PUT request with upload action in snake_case', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/premium/sync`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              task_id: 456,
            },
            message: '',
          });
        }),
      );

      const { forceSync } = useSyncApi();
      const result = await forceSync('upload');

      expect(capturedBody).toEqual({
        action: 'upload',
        async_query: true,
      });
      expect(result.taskId).toBe(456);
    });

    it('should send PUT request with download action in snake_case', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/premium/sync`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              task_id: 789,
            },
            message: '',
          });
        }),
      );

      const { forceSync } = useSyncApi();
      const result = await forceSync('download');

      expect(capturedBody).toEqual({
        action: 'download',
        async_query: true,
      });
      expect(result.taskId).toBe(789);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/premium/sync`, () =>
          HttpResponse.json({
            result: null,
            message: 'Premium subscription required',
          })),
      );

      const { forceSync } = useSyncApi();

      await expect(forceSync('upload'))
        .rejects
        .toThrow('Premium subscription required');
    });
  });
});
