import type { ProfitLossEventsPayload, ProfitLossReportDebugPayload, ProfitLossReportPeriod } from '@/types/reports';
import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useReportsApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/reports/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('generateReport', () => {
    it('sends GET request with snake_case params', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/history`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { generateReport } = useReportsApi();
      const payload: ProfitLossReportPeriod = {
        start: 1700000000,
        end: 1700100000,
      };
      const result = await generateReport(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('from_timestamp')).toBe('1700000000');
      expect(capturedParams!.get('to_timestamp')).toBe('1700100000');
      expect(result.taskId).toBe(123);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to generate report',
          })),
      );

      const { generateReport } = useReportsApi();

      await expect(generateReport({ start: 0, end: 0 }))
        .rejects
        .toThrow('Failed to generate report');
    });
  });

  describe('exportReportCSV', () => {
    it('sends GET request with directory path in snake_case', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/history/export`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { exportReportCSV } = useReportsApi();
      const result = await exportReportCSV('/home/user/reports');

      expect(capturedParams!.get('directory_path')).toBe('/home/user/reports');
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/export`, () =>
          HttpResponse.json({
            result: null,
            message: 'Export failed',
          })),
      );

      const { exportReportCSV } = useReportsApi();

      await expect(exportReportCSV('/invalid'))
        .rejects
        .toThrow('Export failed');
    });
  });

  describe('downloadReportCSV', () => {
    it('returns success on 200 response', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/download`, () =>
          new HttpResponse(new Blob(['zip content'], { type: 'application/zip' }), {
            status: 200,
            headers: {
              'Content-Type': 'application/zip',
            },
          })),
      );

      const { downloadReportCSV } = useReportsApi();
      const result = await downloadReportCSV();

      expect(result.success).toBe(true);
    });

    it('returns failure with message on error response', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/download`, () =>
          HttpResponse.json({
            result: null,
            message: 'No report available',
          }, {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          })),
      );

      const { downloadReportCSV } = useReportsApi();
      const result = await downloadReportCSV();

      expect(result.success).toBe(false);
      if (!result.success)
        expect(result.message).toBe('No report available');
    });
  });

  describe('exportReportData', () => {
    it('sends POST request with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/history/debug`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { exportReportData } = useReportsApi();
      const payload: ProfitLossReportDebugPayload = {
        fromTimestamp: 1700000000,
        toTimestamp: 1700100000,
        directoryPath: '/home/user/debug',
      };
      const result = await exportReportData(payload);

      expect(capturedBody).toEqual({
        async_query: true,
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
        directory_path: '/home/user/debug',
      });
      expect(result.taskId).toBe(456);
    });

    it('sends POST without directoryPath when not provided', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/history/debug`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 789 },
            message: '',
          });
        }),
      );

      const { exportReportData } = useReportsApi();
      await exportReportData({
        fromTimestamp: 1700000000,
        toTimestamp: 1700100000,
      });

      expect(capturedBody).toEqual({
        async_query: true,
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/history/debug`, () =>
          HttpResponse.json({
            result: null,
            message: 'Export debug data failed',
          })),
      );

      const { exportReportData } = useReportsApi();

      await expect(exportReportData({ fromTimestamp: 0, toTimestamp: 0 }))
        .rejects
        .toThrow('Export debug data failed');
    });
  });

  describe('importReportData', () => {
    it('sends PUT request with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/history/debug`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 101 },
            message: '',
          });
        }),
      );

      const { importReportData } = useReportsApi();
      const result = await importReportData('/path/to/debug.json');

      expect(capturedBody).toEqual({
        async_query: true,
        filepath: '/path/to/debug.json',
      });
      expect(result.taskId).toBe(101);
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/history/debug`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid debug file',
          })),
      );

      const { importReportData } = useReportsApi();

      await expect(importReportData('/invalid.json'))
        .rejects
        .toThrow('Invalid debug file');
    });
  });

  describe('uploadReportData', () => {
    it('sends PATCH request with FormData', async () => {
      let capturedContentType = '';
      let capturedFormData: FormData | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/history/debug`, async ({ request }) => {
          capturedContentType = request.headers.get('content-type') ?? '';
          capturedFormData = await request.formData();
          return HttpResponse.json({
            result: { task_id: 202 },
            message: '',
          });
        }),
      );

      const { uploadReportData } = useReportsApi();
      const file = new File(['debug data'], 'debug.json', { type: 'application/json' });
      const result = await uploadReportData(file);

      expect(capturedContentType).toContain('multipart/form-data');
      expect(capturedFormData!.get('async_query')).toBe('true');
      expect(capturedFormData!.get('filepath')).toBeInstanceOf(File);
      expect(result.taskId).toBe(202);
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/history/debug`, () =>
          HttpResponse.json({
            result: null,
            message: 'Upload failed',
          })),
      );

      const { uploadReportData } = useReportsApi();
      const file = new File(['invalid'], 'bad.json');

      await expect(uploadReportData(file))
        .rejects
        .toThrow('Upload failed');
    });
  });

  describe('fetchActionableItems', () => {
    it('fetches and parses actionable items', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/actionable_items`, () =>
          HttpResponse.json({
            result: {
              missing_acquisitions: [
                {
                  asset: 'ETH',
                  found_amount: '0.5',
                  missing_amount: '1.0',
                  time: 1700000000,
                },
              ],
              missing_prices: [
                {
                  from_asset: 'ETH',
                  to_asset: 'USD',
                  time: 1700000000,
                  rate_limited: false,
                },
              ],
            },
            message: '',
          })),
      );

      const { fetchActionableItems } = useReportsApi();
      const result = await fetchActionableItems();

      expect(result.missingAcquisitions).toHaveLength(1);
      expect(result.missingAcquisitions[0].asset).toBe('ETH');
      expect(result.missingAcquisitions[0].foundAmount).toBeInstanceOf(BigNumber);
      expect(result.missingAcquisitions[0].foundAmount.toString()).toBe('0.5');
      expect(result.missingPrices).toHaveLength(1);
      expect(result.missingPrices[0].fromAsset).toBe('ETH');
    });

    it('handles empty actionable items', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/actionable_items`, () =>
          HttpResponse.json({
            result: {
              missing_acquisitions: [],
              missing_prices: [],
            },
            message: '',
          })),
      );

      const { fetchActionableItems } = useReportsApi();
      const result = await fetchActionableItems();

      expect(result.missingAcquisitions).toEqual([]);
      expect(result.missingPrices).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/history/actionable_items`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch actionable items',
          })),
      );

      const { fetchActionableItems } = useReportsApi();

      await expect(fetchActionableItems())
        .rejects
        .toThrow('Failed to fetch actionable items');
    });
  });

  describe('fetchReports', () => {
    it('fetches and parses reports list', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/reports`, () =>
          HttpResponse.json({
            result: {
              entries: [
                {
                  identifier: 1,
                  start_ts: 1700000000,
                  end_ts: 1700100000,
                  timestamp: 1700100001,
                  first_processed_timestamp: 1700000001,
                  last_processed_timestamp: 1700099999,
                  processed_actions: 100,
                  total_actions: 100,
                  overview: {
                    ETH: { free: '1.0', taxable: '0.5' },
                  },
                  settings: {
                    calculate_past_cost_basis: true,
                    include_crypto2crypto: true,
                    include_fees_in_cost_basis: true,
                    include_gas_costs: true,
                    account_for_assets_movements: true,
                    taxfree_after_period: 365,
                    cost_basis_method: 'fifo',
                  },
                },
              ],
              entries_found: 1,
              entries_limit: 100,
            },
            message: '',
          })),
      );

      const { fetchReports } = useReportsApi();
      const result = await fetchReports();

      expect(result.entries).toHaveLength(1);
      expect(result.entries[0].identifier).toBe(1);
      expect(result.entries[0].startTs).toBe(1700000000);
      expect(result.entries[0].overview.ETH.free).toBeInstanceOf(BigNumber);
      expect(result.entries[0].overview.ETH.free.toString()).toBe('1');
      expect(result.entriesFound).toBe(1);
    });

    it('handles empty reports list', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/reports`, () =>
          HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 100,
            },
            message: '',
          })),
      );

      const { fetchReports } = useReportsApi();
      const result = await fetchReports();

      expect(result.entries).toEqual([]);
      expect(result.entriesFound).toBe(0);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/reports`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch reports',
          })),
      );

      const { fetchReports } = useReportsApi();

      await expect(fetchReports())
        .rejects
        .toThrow('Failed to fetch reports');
    });
  });

  describe('fetchReport', () => {
    it('fetches and parses single report overview', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/reports/1`, () =>
          HttpResponse.json({
            result: {
              entries: [
                {
                  ETH: { free: '2.0', taxable: '1.0' },
                  BTC: { free: '0.5', taxable: '0.25' },
                },
              ],
              entries_found: 1,
              entries_limit: 1,
            },
            message: '',
          })),
      );

      const { fetchReport } = useReportsApi();
      const result = await fetchReport(1);

      expect(result.ETH.free).toBeInstanceOf(BigNumber);
      expect(result.ETH.free.toString()).toBe('2');
      expect(result.ETH.taxable).toBeInstanceOf(BigNumber);
      expect(result.ETH.taxable.toString()).toBe('1');
      expect(result.BTC.free).toBeInstanceOf(BigNumber);
      expect(result.BTC.free.toString()).toBe('0.5');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/reports/999`, () =>
          HttpResponse.json({
            result: null,
            message: 'Report not found',
          })),
      );

      const { fetchReport } = useReportsApi();

      await expect(fetchReport(999))
        .rejects
        .toThrow('Report not found');
    });
  });

  describe('fetchReportEvents', () => {
    it('sends POST request with snake_case payload (excluding reportId)', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.post(`${backendUrl}/api/1/reports/:reportId/data`, async ({ request, params }) => {
          capturedUrl = `/reports/${String(params.reportId)}/data`;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [
                {
                  asset_identifier: 'ETH',
                  cost_basis: {
                    is_complete: true,
                    matched_acquisitions: [],
                  },
                  free_amount: '1.0',
                  group_id: null,
                  location: 'binance',
                  notes: 'Test event',
                  pnl_free: '100',
                  pnl_taxable: '50',
                  price: '2000',
                  taxable_amount: '0.5',
                  timestamp: 1700000000,
                  type: 'trade',
                },
              ],
              entries_found: 1,
              entries_limit: 100,
              entries_total: 1,
            },
            message: '',
          });
        }),
      );

      const { fetchReportEvents } = useReportsApi();
      const payload: ProfitLossEventsPayload = {
        reportId: 1,
        limit: 50,
        offset: 0,
        ascending: [false],
        orderByAttributes: ['timestamp'],
      };
      const result = await fetchReportEvents(payload);

      expect(capturedUrl).toBe('/reports/1/data');
      expect(capturedBody).toEqual({
        limit: 50,
        offset: 0,
        ascending: [false],
        order_by_attributes: ['timestamp'],
      });
      expect(result.entries).toHaveLength(1);
      expect(result.entries[0].assetIdentifier).toBe('ETH');
      expect(result.entries[0].pnlFree).toBeInstanceOf(BigNumber);
      expect(result.entries[0].pnlFree.toString()).toBe('100');
    });

    it('handles null cost_basis', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/reports/:reportId/data`, () =>
          HttpResponse.json({
            result: {
              entries: [
                {
                  asset_identifier: 'BTC',
                  cost_basis: null,
                  free_amount: '0.1',
                  group_id: null,
                  location: 'kraken',
                  notes: null,
                  pnl_free: '0',
                  pnl_taxable: '0',
                  price: '40000',
                  taxable_amount: '0',
                  timestamp: 1700000000,
                  type: 'receive',
                },
              ],
              entries_found: 1,
              entries_limit: 100,
              entries_total: 1,
            },
            message: '',
          })),
      );

      const { fetchReportEvents } = useReportsApi();
      const result = await fetchReportEvents({ reportId: 1, limit: 50, offset: 0 });

      expect(result.entries[0].costBasis).toBeNull();
      expect(result.entries[0].notes).toBeNull();
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/reports/:reportId/data`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch report events',
          })),
      );

      const { fetchReportEvents } = useReportsApi();

      await expect(fetchReportEvents({ reportId: 1, limit: 50, offset: 0 }))
        .rejects
        .toThrow('Failed to fetch report events');
    });
  });

  describe('deleteReport', () => {
    it('sends DELETE request for report ID', async () => {
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/reports/:reportId`, ({ params }) => {
          capturedUrl = `/reports/${String(params.reportId)}`;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteReport } = useReportsApi();
      const result = await deleteReport(1);

      expect(capturedUrl).toBe('/reports/1');
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/reports/:reportId`, () =>
          HttpResponse.json({
            result: null,
            message: 'Report not found',
          })),
      );

      const { deleteReport } = useReportsApi();

      await expect(deleteReport(999))
        .rejects
        .toThrow('Report not found');
    });
  });
});
