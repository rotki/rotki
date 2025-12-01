import type { ExchangeFormData, ExchangeSavingsRequestPayload } from '@/types/exchanges';
import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExchangeApi } from './exchanges';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/exchanges', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryRemoveExchange', () => {
    it('sends DELETE request with exchange data', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/exchanges`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { queryRemoveExchange } = useExchangeApi();
      const result = await queryRemoveExchange({ location: 'binance', name: 'my_binance' });

      expect(capturedBody).toEqual({
        location: 'binance',
        name: 'my_binance',
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/exchanges`, () =>
          HttpResponse.json({
            result: null,
            message: 'Exchange not found',
          })),
      );

      const { queryRemoveExchange } = useExchangeApi();

      await expect(queryRemoveExchange({ location: 'binance', name: 'unknown' }))
        .rejects
        .toThrow('Exchange not found');
    });
  });

  describe('queryExchangeBalances', () => {
    it('fetches exchange balances with async_query param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/exchanges/balances/binance`, ({ request }) => {
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

      const { queryExchangeBalances } = useExchangeApi();
      const result = await queryExchangeBalances('binance');

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('includes ignore_cache and usd_value_threshold when provided', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/exchanges/balances/kraken`, ({ request }) => {
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

      const { queryExchangeBalances } = useExchangeApi();
      await queryExchangeBalances('kraken', true, '1000');

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('ignore_cache')).toBe('true');
      expect(capturedParams!.get('usd_value_threshold')).toBe('1000');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/exchanges/balances/binance`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch balances',
          })),
      );

      const { queryExchangeBalances } = useExchangeApi();

      await expect(queryExchangeBalances('binance'))
        .rejects
        .toThrow('Failed to fetch balances');
    });
  });

  describe('callSetupExchange', () => {
    it('sends PUT request for add mode with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let requestMethod = '';

      server.use(
        http.put(`${backendUrl}/api/1/exchanges`, async ({ request }) => {
          requestMethod = request.method;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { callSetupExchange } = useExchangeApi();
      const payload: ExchangeFormData = {
        mode: 'add',
        name: 'my_binance',
        location: 'binance',
        apiKey: 'key123',
        apiSecret: 'secret456',
        passphrase: '',
      };

      const result = await callSetupExchange(payload);

      expect(requestMethod).toBe('PUT');
      expect(capturedBody).toEqual({
        name: 'my_binance',
        location: 'binance',
        api_key: 'key123',
        api_secret: 'secret456',
      });
      expect(result).toBe(true);
    });

    it('sends PATCH request for edit mode with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let requestMethod = '';

      server.use(
        http.patch(`${backendUrl}/api/1/exchanges`, async ({ request }) => {
          requestMethod = request.method;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { callSetupExchange } = useExchangeApi();
      const payload: ExchangeFormData = {
        mode: 'edit',
        name: 'my_binance',
        location: 'binance',
        apiKey: 'new_key',
        apiSecret: 'new_secret',
        passphrase: '',
        binanceMarkets: ['BTCUSDT', 'ETHUSDT'],
      };

      const result = await callSetupExchange(payload);

      expect(requestMethod).toBe('PATCH');
      expect(capturedBody).toEqual({
        name: 'my_binance',
        location: 'binance',
        api_key: 'new_key',
        api_secret: 'new_secret',
        binance_markets: ['BTCUSDT', 'ETHUSDT'],
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/exchanges`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid API credentials',
          })),
      );

      const { callSetupExchange } = useExchangeApi();

      await expect(callSetupExchange({
        mode: 'add',
        name: 'test',
        location: 'binance',
        apiKey: 'bad_key',
        apiSecret: 'bad_secret',
        passphrase: '',
      }))
        .rejects
        .toThrow('Invalid API credentials');
    });
  });

  describe('getExchanges', () => {
    it('fetches list of exchanges', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/exchanges`, () =>
          HttpResponse.json({
            result: [
              { location: 'binance', name: 'my_binance' },
              { location: 'kraken', name: 'my_kraken' },
            ],
            message: '',
          })),
      );

      const { getExchanges } = useExchangeApi();
      const result = await getExchanges();

      expect(result).toHaveLength(2);
      expect(result[0].location).toBe('binance');
      expect(result[1].location).toBe('kraken');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/exchanges`, () =>
          HttpResponse.json({
            result: null,
            message: 'Session expired',
          })),
      );

      const { getExchanges } = useExchangeApi();

      await expect(getExchanges())
        .rejects
        .toThrow('Session expired');
    });
  });

  describe('queryBinanceMarkets', () => {
    it('fetches binance markets with location param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/exchanges/binance/pairs`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
            message: '',
          });
        }),
      );

      const { queryBinanceMarkets } = useExchangeApi();
      const result = await queryBinanceMarkets('binance');

      expect(capturedParams!.get('location')).toBe('binance');
      expect(result).toEqual(['BTCUSDT', 'ETHUSDT', 'BNBUSDT']);
    });
  });

  describe('queryBinanceUserMarkets', () => {
    it('fetches user-specific binance markets', async () => {
      let capturedParams: URLSearchParams | null = null;
      let capturedUrl = '';

      server.use(
        http.get(`${backendUrl}/api/1/exchanges/binance/pairs/my_binance`, ({ request }) => {
          capturedUrl = request.url;
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: ['BTCUSDT', 'ETHUSDT'],
            message: '',
          });
        }),
      );

      const { queryBinanceUserMarkets } = useExchangeApi();
      const result = await queryBinanceUserMarkets('my_binance', 'binance');

      expect(capturedUrl).toContain('/pairs/my_binance');
      expect(capturedParams!.get('location')).toBe('binance');
      expect(result).toEqual(['BTCUSDT', 'ETHUSDT']);
    });
  });

  describe('deleteExchangeData', () => {
    it('deletes all exchange data when no name specified', async () => {
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/exchanges/data`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteExchangeData } = useExchangeApi();
      const result = await deleteExchangeData();

      expect(capturedUrl).toContain('/exchanges/data');
      expect(capturedUrl).not.toContain('/exchanges/data/');
      expect(result).toBe(true);
    });

    it('deletes specific exchange data', async () => {
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/exchanges/data/my_binance`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteExchangeData } = useExchangeApi();
      const result = await deleteExchangeData('my_binance');

      expect(capturedUrl).toContain('/exchanges/data/my_binance');
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/exchanges/data`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete data',
          })),
      );

      const { deleteExchangeData } = useExchangeApi();

      await expect(deleteExchangeData())
        .rejects
        .toThrow('Failed to delete data');
    });
  });

  describe('getExchangeSavingsTask', () => {
    it('sends POST request with snake_case payload and async_query true', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/exchanges/binance/savings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 789,
            },
            message: '',
          });
        }),
      );

      const { getExchangeSavingsTask } = useExchangeApi();
      const payload: ExchangeSavingsRequestPayload = {
        location: 'binance',
        fromTimestamp: 1700000000,
        toTimestamp: 1700100000,
        limit: 100,
        offset: 0,
      };

      const result = await getExchangeSavingsTask(payload);

      expect(capturedBody).toMatchObject({
        async_query: true,
        location: 'binance',
        from_timestamp: 1700000000,
        to_timestamp: 1700100000,
      });
      expect(result.taskId).toBe(789);
    });
  });

  describe('getExchangeSavings', () => {
    it('sends POST request with async_query false and returns parsed response', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/exchanges/kraken/savings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [
                {
                  amount: '1.5',
                  asset: 'ETH',
                  location: 'kraken',
                  timestamp: 1700000000,
                },
              ],
              entries_found: 1,
              entries_limit: 100,
              entries_total: 1,
              total_usd_value: '3000.00',
              assets: ['ETH'],
              received: [
                { asset: 'ETH', amount: '1.5', usd_value: '3000.00' },
              ],
            },
            message: '',
          });
        }),
      );

      const { getExchangeSavings } = useExchangeApi();
      const payload: ExchangeSavingsRequestPayload = {
        location: 'kraken',
        limit: 100,
        offset: 0,
      };

      const result = await getExchangeSavings(payload);

      expect(capturedBody).toMatchObject({
        location: 'kraken',
      });
      expect(result.entries).toHaveLength(1);
      expect(result.entriesFound).toBe(1);
      expect(result.totalUsdValue).toBeInstanceOf(BigNumber);
      expect(result.totalUsdValue.toString()).toBe('3000');
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/exchanges/binance/savings`, () =>
          HttpResponse.json({
            result: null,
            message: 'Savings not available',
          })),
      );

      const { getExchangeSavings } = useExchangeApi();

      await expect(getExchangeSavings({ location: 'binance', limit: 100, offset: 0 }))
        .rejects
        .toThrow('Savings not available');
    });
  });
});
