import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEth2Api } from './eth2';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/staking/eth2', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchStakingPerformance', () => {
    it('fetches staking performance with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries_found: 10,
              entries_total: 100,
              sums: {
                apr: '5.5',
                sum: '1000',
                withdrawals: '50',
              },
              validators: {
                12345: {
                  apr: '5.2',
                  sum: '100',
                },
                12346: {
                  apr: '5.8',
                  sum: '200',
                },
              },
            },
            message: '',
          });
        }),
      );

      const { fetchStakingPerformance } = useEth2Api();
      const result = await fetchStakingPerformance({
        limit: 10,
        offset: 0,
        fromTimestamp: 1700000000,
        toTimestamp: 1700100000,
      });

      expect(capturedBody).toEqual({
        async_query: false,
        ignore_cache: false,
        limit: 10,
        offset: 0,
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
      });
      expect(result.entriesFound).toBe(10);
      expect(result.entriesTotal).toBe(100);
      expect(result.sums.apr).toBeInstanceOf(BigNumber);
      expect(result.sums.apr?.toString()).toBe('5.5');
      expect(result.validators['12345'].apr).toBeInstanceOf(BigNumber);
      expect(result.validators['12345'].apr?.toString()).toBe('5.2');
    });

    it('handles optional payload fields', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries_found: 5,
              entries_total: 50,
              sums: {},
              validators: {},
            },
            message: '',
          });
        }),
      );

      const { fetchStakingPerformance } = useEth2Api();
      await fetchStakingPerformance({
        limit: 20,
        offset: 10,
        validatorIndices: [12345, 12346],
        addresses: ['0x1234', '0x5678'],
        status: 'active',
      });

      expect(capturedBody).toEqual({
        async_query: false,
        ignore_cache: false,
        limit: 20,
        offset: 10,
        validator_indices: [12345, 12346],
        addresses: ['0x1234', '0x5678'],
        status: 'active',
      });
    });

    it('handles empty validators response', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, () =>
          HttpResponse.json({
            result: {
              entries_found: 0,
              entries_total: 0,
              sums: {},
              validators: {},
            },
            message: '',
          })),
      );

      const { fetchStakingPerformance } = useEth2Api();
      const result = await fetchStakingPerformance({
        limit: 10,
        offset: 0,
      });

      expect(result.entriesFound).toBe(0);
      expect(result.validators).toEqual({});
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch staking performance',
          })),
      );

      const { fetchStakingPerformance } = useEth2Api();

      await expect(fetchStakingPerformance({ limit: 10, offset: 0 }))
        .rejects
        .toThrow('Failed to fetch staking performance');
    });
  });

  describe('refreshStakingPerformance', () => {
    it('sends async request with ignore_cache true', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { refreshStakingPerformance } = useEth2Api();
      const result = await refreshStakingPerformance({
        limit: 10,
        offset: 0,
      });

      expect(capturedBody).toEqual({
        async_query: true,
        ignore_cache: true,
        limit: 10,
        offset: 0,
      });
      expect(result.taskId).toBe(123);
    });

    it('includes all payload fields in refresh request', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { refreshStakingPerformance } = useEth2Api();
      await refreshStakingPerformance({
        limit: 50,
        offset: 25,
        validatorIndices: [100, 200, 300],
        status: 'exited',
        fromTimestamp: 1600000000,
        toTimestamp: 1700000000,
      });

      expect(capturedBody).toEqual({
        async_query: true,
        ignore_cache: true,
        limit: 50,
        offset: 25,
        validator_indices: [100, 200, 300],
        status: 'exited',
        from_timestamp: 1600000000,
        to_timestamp: 1700000000,
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/stake/performance`, () =>
          HttpResponse.json({
            result: null,
            message: 'ETH2 staking refresh failed',
          })),
      );

      const { refreshStakingPerformance } = useEth2Api();

      await expect(refreshStakingPerformance({ limit: 10, offset: 0 }))
        .rejects
        .toThrow('ETH2 staking refresh failed');
    });
  });
});
