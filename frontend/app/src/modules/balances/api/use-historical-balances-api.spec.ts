import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/historical-balances', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function getApi(): Promise<ReturnType<typeof import('./use-historical-balances-api').useHistoricalBalancesApi>> {
    const { useHistoricalBalancesApi } = await import('./use-historical-balances-api');
    return useHistoricalBalancesApi();
  }

  describe('fetchHistoricalBalanceSeries', () => {
    it('should request the balance series as an async task with required fields', async () => {
      let capturedBody: DefaultBodyType = null;
      server.use(
        http.post(`${backendUrl}/api/1/balances/historical/asset/series`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ message: '', result: { task_id: 321 } });
        }),
      );

      const { fetchHistoricalBalanceSeries } = await getApi();
      const result = await fetchHistoricalBalanceSeries({ asset: 'ETH', locationLabel: '0xABC' });

      expect(capturedBody).toEqual({
        async_query: true,
        asset: 'ETH',
        location_label: '0xABC',
      });
      expect(result.taskId).toBe(321);
    });

    it('should forward optional location and time range, snake-cased', async () => {
      let capturedBody: DefaultBodyType = null;
      server.use(
        http.post(`${backendUrl}/api/1/balances/historical/asset/series`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ message: '', result: { task_id: 9 } });
        }),
      );

      const { fetchHistoricalBalanceSeries } = await getApi();
      await fetchHistoricalBalanceSeries({
        asset: 'ETH',
        fromTimestamp: 1000,
        location: 'ethereum',
        locationLabel: '0xABC',
        toTimestamp: 2000,
      });

      expect(capturedBody).toEqual({
        async_query: true,
        asset: 'ETH',
        from_timestamp: 1000,
        location: 'ethereum',
        location_label: '0xABC',
        to_timestamp: 2000,
      });
    });
  });
});
