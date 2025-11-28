import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useImportDataApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/import/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('importDataFrom', () => {
    it('sends PUT request with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { importDataFrom } = useImportDataApi();
      const result = await importDataFrom('cointracking', '/path/to/file.csv', '%Y-%m-%d');

      expect(capturedBody).toEqual({
        async_query: true,
        file: '/path/to/file.csv',
        source: 'cointracking',
        timestamp_format: '%Y-%m-%d',
      });
      expect(result.taskId).toBe(123);
    });

    it('handles null timestamp format', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { importDataFrom } = useImportDataApi();
      await importDataFrom('rotki', '/path/to/export.json', null);

      expect(capturedBody).toEqual({
        async_query: true,
        file: '/path/to/export.json',
        source: 'rotki',
        timestamp_format: null,
      });
    });

    it('handles different import sources', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 789 },
            message: '',
          });
        }),
      );

      const { importDataFrom } = useImportDataApi();
      await importDataFrom('cryptocom', '/data/crypto.csv', '%d/%m/%Y');

      expect(capturedBody!.source).toBe('cryptocom');
      expect(capturedBody!.timestamp_format).toBe('%d/%m/%Y');
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/import`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid file format',
          })),
      );

      const { importDataFrom } = useImportDataApi();

      await expect(importDataFrom('cointracking', '/invalid.txt', null))
        .rejects
        .toThrow('Invalid file format');
    });
  });

  describe('importFile', () => {
    it('sends POST request with FormData', async () => {
      let capturedContentType = '';
      let capturedFormData: FormData | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedContentType = request.headers.get('content-type') ?? '';
          capturedFormData = await request.formData();
          return HttpResponse.json({
            result: { task_id: 101 },
            message: '',
          });
        }),
      );

      const { importFile } = useImportDataApi();
      const formData = new FormData();
      formData.append('file', new Blob(['test data'], { type: 'text/csv' }), 'test.csv');
      formData.append('source', 'cointracking');

      const result = await importFile(formData);

      expect(capturedContentType).toContain('multipart/form-data');
      expect(capturedFormData!.get('source')).toBe('cointracking');
      expect(result.taskId).toBe(101);
    });

    it('handles file upload with additional fields', async () => {
      let capturedFormData: FormData | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedFormData = await request.formData();
          return HttpResponse.json({
            result: { task_id: 202 },
            message: '',
          });
        }),
      );

      const { importFile } = useImportDataApi();
      const formData = new FormData();
      formData.append('file', new Blob(['csv,data'], { type: 'text/csv' }), 'trades.csv');
      formData.append('source', 'cryptocom');
      formData.append('timestamp_format', '%Y-%m-%d %H:%M:%S');

      await importFile(formData);

      expect(capturedFormData!.get('source')).toBe('cryptocom');
      expect(capturedFormData!.get('timestamp_format')).toBe('%Y-%m-%d %H:%M:%S');
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/import`, () =>
          HttpResponse.json({
            result: null,
            message: 'File upload failed',
          })),
      );

      const { importFile } = useImportDataApi();
      const formData = new FormData();
      formData.append('file', new Blob(['invalid']), 'bad.csv');

      await expect(importFile(formData))
        .rejects
        .toThrow('File upload failed');
    });
  });
});
