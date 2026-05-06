import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useImportDataApi } from './use-import-data-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/import/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('importDataFrom', () => {
    it('should send PUT request with snake_case payload', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { importDataFrom } = useImportDataApi();
      const result = await importDataFrom({
        file: '/path/to/file.csv',
        source: 'cointracking',
        timestampFormat: '%Y-%m-%d',
        timezone: 'Europe/Madrid',
      });

      expect(capturedBody).toEqual({
        async_query: true,
        file: '/path/to/file.csv',
        source: 'cointracking',
        timestamp_format: '%Y-%m-%d',
        timezone: 'Europe/Madrid',
      });
      expect(result.taskId).toBe(123);
    });

    it('should handle null timestamp format', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { importDataFrom } = useImportDataApi();
      await importDataFrom({
        file: '/path/to/export.json',
        source: 'rotki',
        timestampFormat: null,
        timezone: null,
      });

      expect(capturedBody).toEqual({
        async_query: true,
        file: '/path/to/export.json',
        source: 'rotki',
        timestamp_format: null,
        timezone: null,
      });
    });

    it('should handle different import sources', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { task_id: 789 },
            message: '',
          });
        }),
      );

      const { importDataFrom } = useImportDataApi();
      await importDataFrom({
        file: '/data/crypto.csv',
        source: 'cryptocom',
        timestampFormat: '%d/%m/%Y',
        timezone: null,
      });

      expect(capturedBody).toHaveProperty('source', 'cryptocom');
      expect(capturedBody).toHaveProperty('timestamp_format', '%d/%m/%Y');
    });

    it('should throw error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/import`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid file format',
          })),
      );

      const { importDataFrom } = useImportDataApi();

      await expect(importDataFrom({
        file: '/invalid.txt',
        source: 'cointracking',
        timestampFormat: null,
        timezone: null,
      }))
        .rejects
        .toThrow('Invalid file format');
    });
  });

  describe('importFile', () => {
    it('should send POST request with FormData', async () => {
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

    it('should handle file upload with additional fields', async () => {
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

    it('should throw error on failure', async () => {
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
