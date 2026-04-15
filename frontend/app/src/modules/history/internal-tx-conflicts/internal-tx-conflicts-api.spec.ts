import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HTTPStatus } from '@/modules/api/types/http';
import { useInternalTxConflictsApi } from './internal-tx-conflicts-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('useInternalTxConflictsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchInternalTxConflicts', () => {
    it('should send GET with correct snake_case query params', async () => {
      let capturedUrl: URL | undefined;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/transactions/internal/conflicts`, ({ request }) => {
          capturedUrl = new URL(request.url);
          return HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 20,
              entries_total: 0,
            },
            message: '',
          });
        }),
      );

      const { fetchInternalTxConflicts } = useInternalTxConflictsApi();
      await fetchInternalTxConflicts({ limit: 20, offset: 0 });

      expect(capturedUrl).toBeDefined();
      expect(capturedUrl!.searchParams.get('limit')).toBe('20');
      expect(capturedUrl!.searchParams.get('offset')).toBe('0');
    });

    it('should include tx_hash filter when provided', async () => {
      let capturedUrl: URL | undefined;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/transactions/internal/conflicts`, ({ request }) => {
          capturedUrl = new URL(request.url);
          return HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 20,
              entries_total: 0,
            },
            message: '',
          });
        }),
      );

      const { fetchInternalTxConflicts } = useInternalTxConflictsApi();
      await fetchInternalTxConflicts({ limit: 20, offset: 0, txHash: '0xabc123' });

      expect(capturedUrl).toBeDefined();
      expect(capturedUrl!.searchParams.get('tx_hash')).toBe('0xabc123');
    });

    it('should include fixed and failed boolean filters', async () => {
      let capturedUrl: URL | undefined;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/transactions/internal/conflicts`, ({ request }) => {
          capturedUrl = new URL(request.url);
          return HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 20,
              entries_total: 0,
            },
            message: '',
          });
        }),
      );

      const { fetchInternalTxConflicts } = useInternalTxConflictsApi();
      await fetchInternalTxConflicts({ failed: false, fixed: false, limit: 20, offset: 0 });

      expect(capturedUrl).toBeDefined();
      expect(capturedUrl!.searchParams.get('fixed')).toBe('false');
      expect(capturedUrl!.searchParams.get('failed')).toBe('false');
    });

    it('should parse response with camelCase transformation', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/transactions/internal/conflicts`, () =>
          HttpResponse.json({
            result: {
              entries: [
                {
                  chain: 'ethereum',
                  tx_hash: '0xabc',
                  action: 'repull',
                  repull_reason: 'all_zero_gas',
                  redecode_reason: null,
                  last_retry_ts: 1700000000,
                  last_error: null,
                },
              ],
              entries_found: 1,
              entries_limit: 20,
              entries_total: 1,
            },
            message: '',
          })),
      );

      const { fetchInternalTxConflicts } = useInternalTxConflictsApi();
      const result = await fetchInternalTxConflicts({ limit: 20, offset: 0 });

      expect(result.data).toHaveLength(1);
      expect(result.data[0].txHash).toBe('0xabc');
      expect(result.data[0].repullReason).toBe('all_zero_gas');
      expect(result.data[0].lastRetryTs).toBe(1700000000);
      expect(result.total).toBe(1);
    });

    it('should throw on HTTP error response', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/transactions/internal/conflicts`, () =>
          HttpResponse.json({
            result: null,
            message: 'Server error',
          }, { status: HTTPStatus.INTERNAL_SERVER_ERROR })),
      );

      const { fetchInternalTxConflicts } = useInternalTxConflictsApi();

      await expect(fetchInternalTxConflicts({ limit: 20, offset: 0 }))
        .rejects
        .toThrow();
    });
  });

  describe('fetchInternalTxConflictsCount', () => {
    it('should send POST and return pending and failed counts', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/blockchains/transactions/internal/conflicts`, () =>
          HttpResponse.json({
            result: {
              pending: 178,
              failed: 12,
            },
            message: '',
          })),
      );

      const { fetchInternalTxConflictsCount } = useInternalTxConflictsApi();
      const result = await fetchInternalTxConflictsCount();

      expect(result.pending).toBe(178);
      expect(result.failed).toBe(12);
    });

    it('should throw on HTTP error response', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/blockchains/transactions/internal/conflicts`, () =>
          HttpResponse.json({
            result: null,
            message: 'Server error',
          }, { status: HTTPStatus.INTERNAL_SERVER_ERROR })),
      );

      const { fetchInternalTxConflictsCount } = useInternalTxConflictsApi();

      await expect(fetchInternalTxConflictsCount())
        .rejects
        .toThrow();
    });
  });
});
