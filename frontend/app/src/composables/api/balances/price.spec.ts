import type { SupportedCurrency } from '@/types/currencies';
import type { HistoricPricesPayload } from '@/types/prices';
import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PriceOracle } from '@/types/settings/price-oracle';

vi.unmock('@/composables/api/balances/price');

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/price', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function getApi(): Promise<ReturnType<typeof import('./price').usePriceApi>> {
    const { usePriceApi } = await import('./price');
    return usePriceApi();
  }

  describe('queryPrices', () => {
    it('queries latest prices as async task', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { queryPrices } = await getApi();
      const result = await queryPrices(['ETH', 'BTC'], 'USD', false);

      expect(capturedBody).toEqual({
        assets: ['ETH', 'BTC'],
        async_query: true,
        target_asset: 'USD',
      });
      expect(result.taskId).toBe(123);
    });

    it('includes ignore_cache when set to true', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { queryPrices } = await getApi();
      await queryPrices(['ETH'], 'USD', true);

      expect(capturedBody).toEqual({
        assets: ['ETH'],
        async_query: true,
        ignore_cache: true,
        target_asset: 'USD',
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to query prices',
          })),
      );

      const { queryPrices } = await getApi();

      await expect(queryPrices(['ETH'], 'USD', false))
        .rejects
        .toThrow('Failed to query prices');
    });
  });

  describe('queryCachedPrices', () => {
    it('queries cached prices synchronously and parses response', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              assets: {
                ETH: ['1500.00', 1],
                BTC: ['40000.00', 2],
              },
              oracles: {
                coingecko: 1,
                cryptocompare: 2,
              },
              target_asset: 'USD',
            },
            message: '',
          });
        }),
      );

      const { queryCachedPrices } = await getApi();
      const result = await queryCachedPrices(['ETH', 'BTC'], 'USD');

      expect(capturedBody).toEqual({
        assets: ['ETH', 'BTC'],
        target_asset: 'USD',
      });
      expect(result.ETH.value).toBeInstanceOf(BigNumber);
      expect(result.ETH.value.toString()).toBe('1500');
      expect(result.ETH.oracle).toBe('coingecko');
      expect(result.BTC.value).toBeInstanceOf(BigNumber);
      expect(result.BTC.value.toString()).toBe('40000');
      expect(result.BTC.oracle).toBe('cryptocompare');
    });

    it('identifies manual prices correctly', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest`, () =>
          HttpResponse.json({
            result: {
              assets: {
                ETH: ['2000.00', 3],
              },
              oracles: {
                coingecko: 1,
                manualcurrent: 3,
              },
              target_asset: 'USD',
            },
            message: '',
          })),
      );

      const { queryCachedPrices } = await getApi();
      const result = await queryCachedPrices(['ETH'], 'USD');

      expect(result.ETH.isManualPrice).toBe(true);
      expect(result.ETH.oracle).toBe('manualcurrent');
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest`, () =>
          HttpResponse.json({
            result: null,
            message: 'Price service unavailable',
          })),
      );

      const { queryCachedPrices } = await getApi();

      await expect(queryCachedPrices(['ETH'], 'USD'))
        .rejects
        .toThrow('Price service unavailable');
    });
  });

  describe('queryFiatExchangeRates', () => {
    it('queries fiat exchange rates as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/exchange_rates`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: { task_id: 789 },
            message: '',
          });
        }),
      );

      const { queryFiatExchangeRates } = await getApi();
      const currencies: SupportedCurrency[] = ['EUR', 'GBP', 'JPY'];
      const result = await queryFiatExchangeRates(currencies);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('currencies')).toBe('EUR,GBP,JPY');
      expect(result.taskId).toBe(789);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/exchange_rates`, () =>
          HttpResponse.json({
            result: null,
            message: 'Exchange rate service unavailable',
          })),
      );

      const { queryFiatExchangeRates } = await getApi();

      await expect(queryFiatExchangeRates(['EUR']))
        .rejects
        .toThrow('Exchange rate service unavailable');
    });
  });

  describe('queryHistoricalRate', () => {
    it('queries historical rate as async task', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/historical`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 111 },
            message: '',
          });
        }),
      );

      const { queryHistoricalRate } = await getApi();
      const result = await queryHistoricalRate('ETH', 'USD', 1700000000);

      expect(capturedBody).toEqual({
        assets_timestamp: [['ETH', 1700000000]],
        async_query: true,
        target_asset: 'USD',
      });
      expect(result.taskId).toBe(111);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/historical`, () =>
          HttpResponse.json({
            result: null,
            message: 'Historical price not found',
          })),
      );

      const { queryHistoricalRate } = await getApi();

      await expect(queryHistoricalRate('ETH', 'USD', 1700000000))
        .rejects
        .toThrow('Historical price not found');
    });
  });

  describe('queryHistoricalRates', () => {
    it('queries historical rates as async task', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/historical`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 222 },
            message: '',
          });
        }),
      );

      const { queryHistoricalRates } = await getApi();
      const payload: HistoricPricesPayload = {
        assetsTimestamp: [['ETH', '1700000000'], ['BTC', '1700000000']],
        targetAsset: 'USD',
      };
      const result = await queryHistoricalRates(payload);

      expect(capturedBody).toEqual({
        assets_timestamp: [['ETH', '1700000000'], ['BTC', '1700000000']],
        async_query: true,
        target_asset: 'USD',
      });
      expect(result.taskId).toBe(222);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/historical`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to query historical rates',
          })),
      );

      const { queryHistoricalRates } = await getApi();

      await expect(queryHistoricalRates({ assetsTimestamp: [], targetAsset: 'USD' }))
        .rejects
        .toThrow('Failed to query historical rates');
    });
  });

  describe('queryOnlyCacheHistoricalRates', () => {
    it('queries cached historical rates synchronously', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/historical`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              assets: {
                ETH: {
                  1700000000: '1500.00',
                  1700100000: '1520.00',
                },
              },
              target_asset: 'USD',
            },
            message: '',
          });
        }),
      );

      const { queryOnlyCacheHistoricalRates } = await getApi();
      const payload: Required<HistoricPricesPayload> = {
        assetsTimestamp: [['ETH', '1700000000'], ['ETH', '1700100000']],
        targetAsset: 'USD',
        onlyCachePeriod: 3600,
      };
      const result = await queryOnlyCacheHistoricalRates(payload);

      expect(capturedBody).toEqual({
        assets_timestamp: [['ETH', '1700000000'], ['ETH', '1700100000']],
        only_cache_period: 3600,
        target_asset: 'USD',
      });
      expect(result.assets.ETH['1700000000']).toBeInstanceOf(BigNumber);
      expect(result.assets.ETH['1700000000'].toString()).toBe('1500');
      expect(result.assets.ETH['1700100000']).toBeInstanceOf(BigNumber);
      expect(result.assets.ETH['1700100000'].toString()).toBe('1520');
      expect(result.targetAsset).toBe('USD');
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/historical`, () =>
          HttpResponse.json({
            result: null,
            message: 'Cache lookup failed',
          })),
      );

      const { queryOnlyCacheHistoricalRates } = await getApi();

      await expect(queryOnlyCacheHistoricalRates({
        assetsTimestamp: [],
        targetAsset: 'USD',
        onlyCachePeriod: 3600,
      }))
        .rejects
        .toThrow('Cache lookup failed');
    });
  });

  describe('getPriceCache', () => {
    it('gets oracle price cache', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/oracles/coingecko/cache`, () =>
          HttpResponse.json({
            result: [
              {
                from_asset: 'ETH',
                to_asset: 'USD',
                from_timestamp: '1700000000',
                to_timestamp: '1700100000',
              },
              {
                from_asset: 'BTC',
                to_asset: 'USD',
                from_timestamp: '1700000000',
                to_timestamp: '1700100000',
              },
            ],
            message: '',
          })),
      );

      const { getPriceCache } = await getApi();
      const result = await getPriceCache(PriceOracle.COINGECKO);

      expect(result).toHaveLength(2);
      expect(result[0].fromAsset).toBe('ETH');
      expect(result[0].toAsset).toBe('USD');
      expect(result[0].fromTimestamp).toBe('1700000000');
      expect(result[0].toTimestamp).toBe('1700100000');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/oracles/coingecko/cache`, () =>
          HttpResponse.json({
            result: null,
            message: 'Cache unavailable',
          })),
      );

      const { getPriceCache } = await getApi();

      await expect(getPriceCache(PriceOracle.COINGECKO))
        .rejects
        .toThrow('Cache unavailable');
    });
  });

  describe('createPriceCache', () => {
    it('creates price cache as async task', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/oracles/coingecko/cache`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 333 },
            message: '',
          });
        }),
      );

      const { createPriceCache } = await getApi();
      const result = await createPriceCache(PriceOracle.COINGECKO, 'ETH', 'USD');

      expect(capturedBody).toEqual({
        async_query: true,
        from_asset: 'ETH',
        to_asset: 'USD',
      });
      expect(result.taskId).toBe(333);
    });

    it('includes purge_old when set to true', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/oracles/cryptocompare/cache`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 444 },
            message: '',
          });
        }),
      );

      const { createPriceCache } = await getApi();
      await createPriceCache(PriceOracle.CRYPTOCOMPARE, 'BTC', 'USD', true);

      expect(capturedBody).toEqual({
        async_query: true,
        from_asset: 'BTC',
        purge_old: true,
        to_asset: 'USD',
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/oracles/coingecko/cache`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to create cache',
          })),
      );

      const { createPriceCache } = await getApi();

      await expect(createPriceCache(PriceOracle.COINGECKO, 'ETH', 'USD'))
        .rejects
        .toThrow('Failed to create cache');
    });
  });

  describe('deletePriceCache', () => {
    it('deletes price cache', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/oracles/coingecko/cache`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deletePriceCache } = await getApi();
      const result = await deletePriceCache(PriceOracle.COINGECKO, 'ETH', 'USD');

      expect(capturedBody).toEqual({
        from_asset: 'ETH',
        to_asset: 'USD',
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/oracles/coingecko/cache`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete cache',
          })),
      );

      const { deletePriceCache } = await getApi();

      await expect(deletePriceCache(PriceOracle.COINGECKO, 'ETH', 'USD'))
        .rejects
        .toThrow('Failed to delete cache');
    });
  });
});
