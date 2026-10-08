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

  describe('fetchHistoricalBalances', () => {
    it('should request per-account balances at the timestamp and parse every bucket', async () => {
      let capturedBody: DefaultBodyType = null;
      server.use(
        http.post(`${backendUrl}/api/1/balances/historical`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            message: '',
            result: {
              entries: [
                { amount: '1.5', asset: 'ETH', location: 'ethereum', location_label: '0xABC', protocol: null },
                { amount: '100', asset: 'USDC', location: 'kraken', location_label: 'main', protocol: 'aave' },
              ],
              processing_required: true,
            },
          });
        }),
      );

      const { fetchHistoricalBalances } = await getApi();
      const result = await fetchHistoricalBalances(1700000000);

      expect(capturedBody).toEqual({ group_by_account: true, timestamp: 1700000000 });
      expect(result.processingRequired).toBe(true);
      expect(result.entries.map(({ amount, ...rest }) => ({ amount: amount.toString(), ...rest }))).toEqual([
        { amount: '1.5', asset: 'ETH', location: 'ethereum', locationLabel: '0xABC', protocol: null },
        { amount: '100', asset: 'USDC', location: 'kraken', locationLabel: 'main', protocol: 'aave' },
      ]);
    });

    it('should read a 404 as a date with no holdings', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/balances/historical`, () =>
          HttpResponse.json({ message: 'No historical data found', result: null }, { status: 404 })),
      );

      const { fetchHistoricalBalances } = await getApi();

      await expect(fetchHistoricalBalances(1)).resolves.toEqual({ entries: [], processingRequired: false });
    });

    it('should reject on any other failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/balances/historical`, () =>
          HttpResponse.json({ message: 'boom', result: null }, { status: 500 })),
      );

      const { fetchHistoricalBalances } = await getApi();

      await expect(fetchHistoricalBalances(1)).rejects.toThrow();
    });
  });

  describe('findHistoricalBalanceDivergence', () => {
    it('should request the divergence search as an async task with required fields', async () => {
      let capturedBody: DefaultBodyType = null;
      server.use(
        http.post(`${backendUrl}/api/1/balances/historical/onchain/divergence`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ message: '', result: { task_id: 654 } });
        }),
      );

      const { findHistoricalBalanceDivergence } = await getApi();
      const result = await findHistoricalBalanceDivergence({
        address: '0xABC',
        asset: 'ETH',
        evmChain: 'ethereum',
      });

      expect(capturedBody).toEqual({
        address: '0xABC',
        asset: 'ETH',
        async_query: true,
        evm_chain: 'ethereum',
      });
      expect(result.taskId).toBe(654);
    });

    it('should forward the issue time boundary in seconds, snake-cased', async () => {
      let capturedBody: DefaultBodyType = null;
      server.use(
        http.post(`${backendUrl}/api/1/balances/historical/onchain/divergence`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ message: '', result: { task_id: 655 } });
        }),
      );
      const { findHistoricalBalanceDivergence } = await getApi();
      await findHistoricalBalanceDivergence({
        address: '0xABC',
        asset: 'ETH',
        evmChain: 'ethereum',
        toTimestamp: 1710000000,
      });
      expect(capturedBody).toEqual({
        address: '0xABC',
        asset: 'ETH',
        async_query: true,
        evm_chain: 'ethereum',
        to_timestamp: 1710000000,
      });
    });
  });

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

  it('should fetch event snapshots directly and parse decimal balances', async () => {
    let capturedBody: DefaultBodyType = null;
    server.use(http.post(`${backendUrl}/api/1/balances/historical/events`, async ({ request }) => {
      capturedBody = await request.json();
      return HttpResponse.json({ message: '', result: { entries: {
        123: { processing_required: false, buckets: [{ location: 'ethereum', protocol: null, balance: '0.1234567890123456789' }] },
      } } });
    }));
    const { fetchHistoricalBalancesAtEvents } = await getApi();
    const result = await fetchHistoricalBalancesAtEvents([123]);
    expect(capturedBody).toEqual({ event_identifiers: [123] });
    expect(result.entries['123'].processingRequired).toBe(false);
    expect(result.entries['123'].buckets[0].balance.toString()).toBe('0.1234567890123456789');
  });
});
