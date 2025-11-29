import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSkippedHistoryEventsApi } from '@/composables/api/history/events/skipped';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/history/events/skipped', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getSkippedEventsSummary', () => {
    it('fetches skipped events summary', async () => {
      const mockSummary = {
        locations: {
          binance: 5,
          kraken: 10,
          coinbase: 3,
        },
        total: 18,
      };

      server.use(
        http.get(`${backendUrl}/api/1/history/skipped_external_events`, () =>
          HttpResponse.json({
            result: mockSummary,
            message: '',
          })),
      );

      const { getSkippedEventsSummary } = useSkippedHistoryEventsApi();
      const result = await getSkippedEventsSummary();

      expect(result).toEqual(mockSummary);
    });

    it('handles empty locations', async () => {
      const mockSummary = {
        locations: {},
        total: 0,
      };

      server.use(
        http.get(`${backendUrl}/api/1/history/skipped_external_events`, () =>
          HttpResponse.json({
            result: mockSummary,
            message: '',
          })),
      );

      const { getSkippedEventsSummary } = useSkippedHistoryEventsApi();
      const result = await getSkippedEventsSummary();

      expect(result).toEqual(mockSummary);
    });
  });

  describe('reProcessSkippedEvents', () => {
    it('sends POST request to reprocess skipped events', async () => {
      let requestMethod = '';

      server.use(
        http.post(`${backendUrl}/api/1/history/skipped_external_events`, ({ request }) => {
          requestMethod = request.method;
          return HttpResponse.json({
            result: {
              successful: 15,
              total: 18,
            },
            message: '',
          });
        }),
      );

      const { reProcessSkippedEvents } = useSkippedHistoryEventsApi();
      const result = await reProcessSkippedEvents();

      expect(requestMethod).toBe('POST');
      expect(result).toEqual({
        successful: 15,
        total: 18,
      });
    });

    it('handles case when all events are processed', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/history/skipped_external_events`, () =>
          HttpResponse.json({
            result: {
              successful: 10,
              total: 10,
            },
            message: '',
          })),
      );

      const { reProcessSkippedEvents } = useSkippedHistoryEventsApi();
      const result = await reProcessSkippedEvents();

      expect(result.successful).toBe(result.total);
    });
  });

  describe('exportSkippedEventsCSV', () => {
    it('sends PUT request with directory_path in snake_case', async () => {
      let requestBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/history/skipped_external_events`, async ({ request }) => {
          requestBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { exportSkippedEventsCSV } = useSkippedHistoryEventsApi();
      const result = await exportSkippedEventsCSV('/home/user/exports');

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        directory_path: '/home/user/exports',
      });
    });
  });

  describe('downloadSkippedEventsCSV', () => {
    it('sends PATCH request to download CSV and returns success', async () => {
      let requestMethod = '';
      const csvContent = 'event_id,location,reason\n1,binance,invalid_format';

      server.use(
        http.patch(`${backendUrl}/api/1/history/skipped_external_events`, ({ request }) => {
          requestMethod = request.method;
          return new HttpResponse(csvContent, {
            status: 200,
            headers: {
              'Content-Type': 'text/csv',
              'Content-Disposition': 'attachment; filename="skipped_external_events.csv"',
            },
          });
        }),
      );

      const { downloadSkippedEventsCSV } = useSkippedHistoryEventsApi();
      const result = await downloadSkippedEventsCSV();

      expect(requestMethod).toBe('PATCH');
      expect(result.success).toBe(true);
    });

    it('returns error message on non-200 response', async () => {
      // With ofetch, MSW properly intercepts blob responses and we can test
      // the real error handling behavior where Flask returns JSON error
      server.use(
        http.patch(`${backendUrl}/api/1/history/skipped_external_events`, () =>
          HttpResponse.json(
            { result: null, message: 'No skipped events to export' },
            {
              status: 400,
              headers: { 'Content-Type': 'application/json' },
            },
          )),
      );

      const { downloadSkippedEventsCSV } = useSkippedHistoryEventsApi();
      const result = await downloadSkippedEventsCSV();

      expect(result.success).toBe(false);
      if (!result.success)
        expect(result.message).toBe('No skipped events to export');
    });
  });
});
