import type { AllBalancePayload } from '@/types/blockchain/accounts';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalancesApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryBalancesAsync', () => {
    it('fetches balances with async_query param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 123,
            },
            message: '',
          });
        }),
      );

      const { queryBalancesAsync } = useBalancesApi();
      const result = await queryBalancesAsync({});

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('includes all payload params in snake_case', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 456,
            },
            message: '',
          });
        }),
      );

      const { queryBalancesAsync } = useBalancesApi();
      const payload: Partial<AllBalancePayload> = {
        ignoreCache: true,
        saveData: true,
        ignoreErrors: false,
      };
      await queryBalancesAsync(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('ignore_cache')).toBe('true');
      expect(capturedParams!.get('save_data')).toBe('true');
      expect(capturedParams!.get('ignore_errors')).toBe('false');
    });

    it('handles partial payload', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 789,
            },
            message: '',
          });
        }),
      );

      const { queryBalancesAsync } = useBalancesApi();
      await queryBalancesAsync({ ignoreCache: true });

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('ignore_cache')).toBe('true');
      expect(capturedParams!.get('save_data')).toBeNull();
      expect(capturedParams!.get('ignore_errors')).toBeNull();
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch balances',
          })),
      );

      const { queryBalancesAsync } = useBalancesApi();

      await expect(queryBalancesAsync({}))
        .rejects
        .toThrow('Failed to fetch balances');
    });
  });
});
