import type { HistoricalAssetPricePayload } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useStatisticsApi } from './statistics-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/statistics/statistics-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryNetValueData', () => {
    it('fetches net value data with include_nfts param', async () => {
      let capturedParams: URLSearchParams | null = null;

      const mockNetValue = {
        times: [1700000000, 1700100000],
        data: ['1000.00', '1500.00'],
      };

      server.use(
        http.get(`${backendUrl}/api/1/statistics/netvalue`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: mockNetValue,
            message: '',
          });
        }),
      );

      const { queryNetValueData } = useStatisticsApi();
      const result = await queryNetValueData(true);

      expect(capturedParams!.get('include_nfts')).toBe('true');
      expect(result.times).toEqual([1700000000, 1700100000]);
    });

    it('fetches net value data without NFTs', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/statistics/netvalue`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              times: [],
              data: [],
            },
            message: '',
          });
        }),
      );

      const { queryNetValueData } = useStatisticsApi();
      await queryNetValueData(false);

      expect(capturedParams!.get('include_nfts')).toBe('false');
    });
  });

  describe('queryTimedBalancesData', () => {
    it('sends POST request with snake_case payload for asset', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      // TimedBalances is an array of TimedBalance objects
      const mockBalances = [
        { time: 1700000000, amount: '10.5', usd_value: '1050.00' },
      ];

      server.use(
        http.post(`${backendUrl}/api/1/statistics/balance`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: mockBalances,
            message: '',
          });
        }),
      );

      const { queryTimedBalancesData } = useStatisticsApi();
      const result = await queryTimedBalancesData('ETH', 1700000000, 1700100000);

      expect(capturedBody).toEqual({
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
        asset: 'ETH',
      });
      expect(result).toHaveLength(1);
    });

    it('sends POST request with collection_id when provided', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/statistics/balance`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: [],
            message: '',
          });
        }),
      );

      const { queryTimedBalancesData } = useStatisticsApi();
      await queryTimedBalancesData('ETH', 1700000000, 1700100000, 42);

      expect(capturedBody).toEqual({
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
        collection_id: 42,
      });
      // Should NOT have asset when collectionId is provided
      expect(capturedBody).not.toHaveProperty('asset');
    });
  });

  describe('queryTimedHistoricalBalancesData', () => {
    it('sends POST request to historical asset balances endpoint', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      // TimedAssetHistoricalBalances has times and values arrays
      const mockHistoricalBalances = {
        times: [1700000000, 1700100000],
        values: ['1000.00', '1500.00'],
      };

      server.use(
        http.post(`${backendUrl}/api/1/balances/historical/asset`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: mockHistoricalBalances,
            message: '',
          });
        }),
      );

      const { queryTimedHistoricalBalancesData } = useStatisticsApi();
      await queryTimedHistoricalBalancesData('BTC', 1700000000, 1700200000);

      expect(capturedUrl).toContain('/balances/historical/asset');
      expect(capturedBody).toEqual({
        from_timestamp: 1700000000,
        to_timestamp: 1700200000,
        asset: 'BTC',
      });
    });

    it('uses collection_id instead of asset when provided', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/balances/historical/asset`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              times: [],
              values: [],
            },
            message: '',
          });
        }),
      );

      const { queryTimedHistoricalBalancesData } = useStatisticsApi();
      await queryTimedHistoricalBalancesData('BTC', 1700000000, 1700200000, 99);

      expect(capturedBody).toEqual({
        from_timestamp: 1700000000,
        to_timestamp: 1700200000,
        collection_id: 99,
      });
      expect(capturedBody).not.toHaveProperty('asset');
    });
  });

  describe('queryLatestLocationValueDistribution', () => {
    it('fetches location distribution with correct param', async () => {
      let capturedParams: URLSearchParams | null = null;

      // LocationData is an array of LocationDataItem objects
      const mockLocationData = [
        { location: 'binance', time: 1700000000, usd_value: '5000.00' },
        { location: 'kraken', time: 1700000000, usd_value: '3000.00' },
      ];

      server.use(
        http.get(`${backendUrl}/api/1/statistics/value_distribution`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: mockLocationData,
            message: '',
          });
        }),
      );

      const { queryLatestLocationValueDistribution } = useStatisticsApi();
      const result = await queryLatestLocationValueDistribution();

      expect(capturedParams!.get('distribution_by')).toBe('location');
      expect(result).toHaveLength(2);
      expect(result[0].location).toBe('binance');
    });
  });

  describe('queryLatestAssetValueDistribution', () => {
    it('fetches asset distribution with correct param', async () => {
      let capturedParams: URLSearchParams | null = null;

      // TimedAssetBalances is an array of TimedAssetBalance objects
      const mockAssetData = [
        {
          time: 1700000000,
          amount: '1.5',
          usd_value: '3000.00',
          asset: 'ETH',
        },
      ];

      server.use(
        http.get(`${backendUrl}/api/1/statistics/value_distribution`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: mockAssetData,
            message: '',
          });
        }),
      );

      const { queryLatestAssetValueDistribution } = useStatisticsApi();
      const result = await queryLatestAssetValueDistribution();

      expect(capturedParams!.get('distribution_by')).toBe('asset');
      expect(result).toHaveLength(1);
    });
  });

  describe('queryStatisticsRenderer', () => {
    it('fetches statistics renderer string', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/statistics/renderer`, () =>
          HttpResponse.json({
            result: 'echarts',
            message: '',
          })),
      );

      const { queryStatisticsRenderer } = useStatisticsApi();
      const result = await queryStatisticsRenderer();

      expect(result).toBe('echarts');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/statistics/renderer`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to get renderer',
          })),
      );

      const { queryStatisticsRenderer } = useStatisticsApi();

      await expect(queryStatisticsRenderer())
        .rejects
        .toThrow('Failed to get renderer');
    });
  });

  describe('queryHistoricalAssetPrices', () => {
    it('sends POST request with snake_case payload and async_query', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/balances/historical/asset/prices`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 123,
            },
            message: '',
          });
        }),
      );

      const { queryHistoricalAssetPrices } = useStatisticsApi();
      const payload: HistoricalAssetPricePayload = {
        asset: 'ETH',
        fromTimestamp: 1700000000,
        toTimestamp: 1700100000,
        interval: 3600,
      };

      const result = await queryHistoricalAssetPrices(payload);

      expect(capturedBody).toEqual({
        asset: 'ETH',
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
        interval: 3600,
        async_query: true,
      });
      expect(result.taskId).toBe(123);
    });
  });
});
