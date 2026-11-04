import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useImportDataApi } from './use-import-data-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/import/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('checkImportLocations', () => {
    it('should send a PUT request with location mappings and parse all resolution statuses', async () => {
      let capturedBody: DefaultBodyType = null;
      const locations = [
        { value: 'kraken', status: 'resolved', location: 'kraken', candidates: [] },
        { value: 'Exchange', status: 'ambiguous', location: null, candidates: ['kraken', 'binance'] },
        { value: 'Unknown', status: 'unresolved', location: null, candidates: [] },
      ];

      server.use(
        http.put(`${backendUrl}/api/1/import/preflight`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ result: { locations }, message: '' });
        }),
      );

      const { checkImportLocations } = useImportDataApi();
      const result = await checkImportLocations({
        file: '/path/to/file.csv',
        source: 'rotki_events',
        locationMappings: { Exchange: 'kraken' },
      });

      expect(capturedBody).toEqual({
        file: '/path/to/file.csv',
        source: 'rotki_events',
        location_mappings: { Exchange: 'kraken' },
      });
      expect(result).toEqual(locations);
    });

    it('should send location mapping keys exactly as they appear in the file', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/import/preflight`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ result: { locations: [] }, message: '' });
        }),
      );

      await useImportDataApi().checkImportLocations({
        file: '/path/to/file.csv',
        source: 'rotki_events',
        locationMappings: { myBank: 'kraken' },
      });

      expect(capturedBody).toEqual({
        file: '/path/to/file.csv',
        source: 'rotki_events',
        location_mappings: { myBank: 'kraken' },
      });
    });

    it('should reject malformed preflight responses', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/import/preflight`, () => HttpResponse.json({
          result: {
            locations: [{ value: 'Unknown', status: 'invalid', location: null, candidates: [] }],
          },
          message: '',
        })),
      );

      const { checkImportLocations } = useImportDataApi();
      await expect(checkImportLocations({ file: '/path/to/file.csv', source: 'rotki_events' }))
        .rejects
        .toThrow();
    });
  });

  describe('checkImportFileLocations', () => {
    it('should post the uploaded file with its mappings, and keep a blank location value', async () => {
      let capturedFormData: FormData | null = null;
      const locations = [{ value: '', status: 'unresolved', location: null, candidates: [] }];
      server.use(
        http.post(`${backendUrl}/api/1/import/preflight`, async ({ request }) => {
          capturedFormData = await request.formData();
          return HttpResponse.json({ result: { locations }, message: '' });
        }),
      );
      const data = new FormData();
      data.append('source', 'rotki_events');
      data.append('file', new Blob(['csv,data'], { type: 'text/csv' }), 'events.csv');
      data.append('location_mappings', JSON.stringify({ '': 'external' }));

      expect(await useImportDataApi().checkImportFileLocations(data)).toEqual(locations);
      expect(capturedFormData!.get('source')).toBe('rotki_events');
      expect(capturedFormData!.get('file')).toBeInstanceOf(File);
      expect(capturedFormData!.get('location_mappings')).toBe('{"":"external"}');
    });

    it('should reject malformed preflight responses', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/import/preflight`, () => HttpResponse.json({
          result: { locations: [{ value: 'Unknown', status: 'unresolved', location: null }] },
          message: '',
        })),
      );

      const { checkImportFileLocations } = useImportDataApi();
      await expect(checkImportFileLocations(new FormData()))
        .rejects
        .toThrow();
    });
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

    it('should send location mapping keys exactly as they appear in the file', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/import`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ result: { task_id: 789 }, message: '' });
        }),
      );

      await useImportDataApi().importDataFrom({
        file: '/path/to/file.csv',
        source: 'rotki_events',
        timestampFormat: null,
        timezone: null,
        locationMappings: { myBank: 'kraken' },
      });

      expect(capturedBody).toEqual({
        async_query: true,
        file: '/path/to/file.csv',
        source: 'rotki_events',
        timestamp_format: null,
        timezone: null,
        location_mappings: { myBank: 'kraken' },
      });
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
