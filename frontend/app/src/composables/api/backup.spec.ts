import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.unmock('@/composables/api/backup');

const { useBackupApi } = await import('./backup');

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/backup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useBackupApi', () => {
    describe('info', () => {
      it('sends GET request and returns database info', async () => {
        server.use(
          http.get(`${backendUrl}/api/1/database/info`, () =>
            HttpResponse.json({
              result: {
                globaldb: {
                  globaldb_assets_version: 15,
                  globaldb_schema_version: 8,
                },
                userdb: {
                  info: {
                    filepath: '/data/user.db',
                    size: 1048576,
                    version: 42,
                  },
                  backups: [
                    {
                      size: 524288,
                      time: 1700000000,
                      version: 41,
                    },
                  ],
                },
              },
              message: '',
            })),
        );

        const api = useBackupApi();
        const result = await api.info();

        expect(result.globaldb.globaldbAssetsVersion).toBe(15);
        expect(result.globaldb.globaldbSchemaVersion).toBe(8);
        expect(result.userdb.info.filepath).toBe('/data/user.db');
        expect(result.userdb.info.size).toBe(1048576);
        expect(result.userdb.backups).toHaveLength(1);
        expect(result.userdb.backups[0].version).toBe(41);
      });

      it('returns empty backups array when no backups exist', async () => {
        server.use(
          http.get(`${backendUrl}/api/1/database/info`, () =>
            HttpResponse.json({
              result: {
                globaldb: {
                  globaldb_assets_version: 15,
                  globaldb_schema_version: 8,
                },
                userdb: {
                  info: {
                    filepath: '/data/user.db',
                    size: 512000,
                    version: 1,
                  },
                  backups: [],
                },
              },
              message: '',
            })),
        );

        const api = useBackupApi();
        const result = await api.info();

        expect(result.userdb.backups).toHaveLength(0);
      });
    });

    describe('createBackup', () => {
      it('sends PUT request and returns backup file path', async () => {
        server.use(
          http.put(`${backendUrl}/api/1/database/backups`, () =>
            HttpResponse.json({
              result: '/backups/user_db_v42_1700000000.db',
              message: '',
            })),
        );

        const api = useBackupApi();
        const result = await api.createBackup();

        expect(result).toBe('/backups/user_db_v42_1700000000.db');
      });
    });

    describe('deleteBackup', () => {
      it('sends DELETE request with files array in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/database/backups`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const api = useBackupApi();
        const result = await api.deleteBackup(['backup1.db', 'backup2.db']);

        expect(capturedBody).toEqual({
          files: ['backup1.db', 'backup2.db'],
        });
        expect(result).toBe(true);
      });

      it('throws error on failure', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/database/backups`, () =>
            HttpResponse.json({
              result: false,
              message: 'File not found',
            })),
        );

        const api = useBackupApi();

        // When result is false, handleResponse throws because falsy result triggers error path
        await expect(api.deleteBackup(['nonexistent.db']))
          .rejects
          .toThrow('File not found');
      });
    });

    describe('fileUrl', () => {
      it('returns correct URL for backup file', () => {
        const api = useBackupApi();
        const url = api.fileUrl('backup_v42.db');

        expect(url).toContain('/database/backups?file=backup_v42.db');
      });
    });
  });
});
