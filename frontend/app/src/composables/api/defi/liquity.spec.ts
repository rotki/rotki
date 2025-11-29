import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLiquityApi } from './liquity';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/defi/liquity', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchLiquityBalances', () => {
    it('fetches liquity balances as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/balances`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 1,
            },
            message: '',
          });
        }),
      );

      const { fetchLiquityBalances } = useLiquityApi();
      const result = await fetchLiquityBalances();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(1);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch liquity balances',
          })),
      );

      const { fetchLiquityBalances } = useLiquityApi();

      await expect(fetchLiquityBalances())
        .rejects
        .toThrow('Failed to fetch liquity balances');
    });
  });

  describe('fetchLiquityStaking', () => {
    it('fetches liquity staking as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/staking`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 2,
            },
            message: '',
          });
        }),
      );

      const { fetchLiquityStaking } = useLiquityApi();
      const result = await fetchLiquityStaking();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(2);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/staking`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch liquity staking',
          })),
      );

      const { fetchLiquityStaking } = useLiquityApi();

      await expect(fetchLiquityStaking())
        .rejects
        .toThrow('Failed to fetch liquity staking');
    });
  });

  describe('fetchLiquityStakingPools', () => {
    it('fetches liquity staking pools as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/pool`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 3,
            },
            message: '',
          });
        }),
      );

      const { fetchLiquityStakingPools } = useLiquityApi();
      const result = await fetchLiquityStakingPools();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(3);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/pool`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch liquity staking pools',
          })),
      );

      const { fetchLiquityStakingPools } = useLiquityApi();

      await expect(fetchLiquityStakingPools())
        .rejects
        .toThrow('Failed to fetch liquity staking pools');
    });
  });

  describe('fetchLiquityStatistics', () => {
    it('fetches liquity statistics as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/stats`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 4,
            },
            message: '',
          });
        }),
      );

      const { fetchLiquityStatistics } = useLiquityApi();
      const result = await fetchLiquityStatistics();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(4);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/liquity/stats`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch liquity statistics',
          })),
      );

      const { fetchLiquityStatistics } = useLiquityApi();

      await expect(fetchLiquityStatistics())
        .rejects
        .toThrow('Failed to fetch liquity statistics');
    });
  });
});
