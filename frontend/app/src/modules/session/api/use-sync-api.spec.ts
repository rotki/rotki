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

  describe('fetchRemoteBackup', () => {
    it('should return the backup on the server in camelCase', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/sync`, () =>
          HttpResponse.json({
            result: { backup: { data_hash: 'abc', data_size: 4242, last_modify_ts: 1760882400, upload_ts: 1760882460 } },
            message: '',
          })),
      );

      const { fetchRemoteBackup } = useSyncApi();

      await expect(fetchRemoteBackup()).resolves.toEqual({
        dataHash: 'abc',
        dataSize: 4242,
        lastModifyTs: 1760882400,
        uploadTs: 1760882460,
      });
    });

    it('should return null when the server stores no backup', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/sync`, () =>
          HttpResponse.json({ result: { backup: null }, message: '' })),
      );

      const { fetchRemoteBackup } = useSyncApi();

      await expect(fetchRemoteBackup()).resolves.toBeNull();
    });
  });

  describe('deleteRemoteBackup', () => {
    it('should send the reviewed hash in snake_case', async () => {
      let capturedBody: DefaultBodyType = null;
      server.use(
        http.delete(`${backendUrl}/api/1/premium/sync`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ result: { premium_should_sync: false }, message: '' });
        }),
      );

      const { deleteRemoteBackup } = useSyncApi();
      const result = await deleteRemoteBackup({ dataHash: 'abc', disableSync: true });

      expect(capturedBody).toEqual({ data_hash: 'abc', disable_sync: true });
      expect(result).toEqual({ premiumShouldSync: false });
    });

    it('should carry the cause when the server kept a changed backup', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/premium/sync`, () =>
          HttpResponse.json(
            { result: null, message: 'The backup on the rotki server changed', cause: 'conflict' },
            { status: 502 },
          )),
      );

      const { deleteRemoteBackup } = useSyncApi();

      await expect(deleteRemoteBackup({ dataHash: 'abc', disableSync: true }))
        .rejects
        .toMatchObject({ failureCause: 'conflict', message: 'The backup on the rotki server changed', status: 502 });
    });

    it('should carry the cause when the server has no backup', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/premium/sync`, () =>
          HttpResponse.json(
            { result: null, message: 'There is no backup', cause: 'not_found' },
            { status: 502 },
          )),
      );

      const { deleteRemoteBackup } = useSyncApi();

      await expect(deleteRemoteBackup({ dataHash: 'abc', disableSync: true }))
        .rejects
        .toMatchObject({ failureCause: 'not_found', status: 502 });
    });
  });
});
