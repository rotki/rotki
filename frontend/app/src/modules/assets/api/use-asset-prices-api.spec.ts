import type { HistoricalPriceDeletePayload, HistoricalPriceFormPayload, ManualPriceFormPayload, ManualPricePayload } from '@/modules/assets/prices/price-types';
import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetPricesApi } from './use-asset-prices-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/assets/prices', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchHistoricalPrices', () => {
    it('should fetch historical prices without payload', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/assets/prices/historical`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: [
              {
                from_asset: 'ETH',
                to_asset: 'USD',
                price: '2000',
                timestamp: 1700000000,
              },
            ],
            message: '',
          });
        }),
      );

      const { fetchHistoricalPrices } = useAssetPricesApi();
      const result = await fetchHistoricalPrices();

      expect(capturedParams!.toString()).toBe('');
      expect(result).toHaveLength(1);
      expect(result[0].fromAsset).toBe('ETH');
      expect(result[0].toAsset).toBe('USD');
      expect(result[0].price).toBeInstanceOf(BigNumber);
      expect(result[0].price.toString()).toBe('2000');
    });

    it('should fetch historical prices with payload in snake_case', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/assets/prices/historical`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: [],
            message: '',
          });
        }),
      );

      const { fetchHistoricalPrices } = useAssetPricesApi();
      const payload: Partial<ManualPricePayload> = {
        fromAsset: 'BTC',
        toAsset: 'EUR',
      };
      await fetchHistoricalPrices(payload);

      expect(capturedParams!.get('from_asset')).toBe('BTC');
      expect(capturedParams!.get('to_asset')).toBe('EUR');
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/assets/prices/historical`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch historical prices',
          })),
      );

      const { fetchHistoricalPrices } = useAssetPricesApi();

      await expect(fetchHistoricalPrices())
        .rejects
        .toThrow('Failed to fetch historical prices');
    });
  });

  describe('addHistoricalPrice', () => {
    it('should send PUT request with snake_case payload', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/prices/historical`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addHistoricalPrice } = useAssetPricesApi();
      const payload: HistoricalPriceFormPayload = {
        fromAsset: 'ETH',
        toAsset: 'USD',
        price: '2500',
        sourceType: 'manual',
        timestamp: 1700000000,
      };
      const result = await addHistoricalPrice(payload);

      expect(capturedBody).toEqual({
        from_asset: 'ETH',
        to_asset: 'USD',
        price: '2500',
        source_type: 'manual',
        timestamp: 1700000000,
      });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/prices/historical`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid price data',
          })),
      );

      const { addHistoricalPrice } = useAssetPricesApi();

      await expect(addHistoricalPrice({
        fromAsset: 'ETH',
        toAsset: 'USD',
        price: '-100',
        sourceType: 'manual',
        timestamp: 1700000000,
      }))
        .rejects
        .toThrow('Invalid price data');
    });
  });

  describe('editHistoricalPrice', () => {
    it('should send PATCH request with snake_case payload', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.patch(`${backendUrl}/api/1/assets/prices/historical`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editHistoricalPrice } = useAssetPricesApi();
      const payload: HistoricalPriceFormPayload = {
        fromAsset: 'BTC',
        toAsset: 'EUR',
        price: '45000',
        sourceType: 'manual',
        timestamp: 1700100000,
      };
      const result = await editHistoricalPrice(payload);

      expect(capturedBody).toEqual({
        from_asset: 'BTC',
        to_asset: 'EUR',
        price: '45000',
        source_type: 'manual',
        timestamp: 1700100000,
      });
      expect(result).toBe(true);
    });
  });

  describe('deleteHistoricalPrice', () => {
    it('should send DELETE request with snake_case payload in body', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/prices/historical`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteHistoricalPrice } = useAssetPricesApi();
      const payload: HistoricalPriceDeletePayload = {
        fromAsset: 'ETH',
        toAsset: 'USD',
        sourceType: 'manual',
        timestamp: 1700000000,
      };
      const result = await deleteHistoricalPrice(payload);

      expect(capturedBody).toEqual({
        from_asset: 'ETH',
        to_asset: 'USD',
        source_type: 'manual',
        timestamp: 1700000000,
      });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/prices/historical`, () =>
          HttpResponse.json({
            result: null,
            message: 'Price not found',
          })),
      );

      const { deleteHistoricalPrice } = useAssetPricesApi();

      await expect(deleteHistoricalPrice({
        fromAsset: 'ETH',
        toAsset: 'USD',
        sourceType: 'manual',
        timestamp: 0,
      }))
        .rejects
        .toThrow('Price not found');
    });
  });

  describe('fetchLatestPrices', () => {
    it('should send POST request without payload', async () => {
      let capturedBody: unknown = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest/all`, async ({ request }) => {
          const text = await request.text();
          capturedBody = text ? JSON.parse(text) : null;
          return HttpResponse.json({
            result: [
              {
                from_asset: 'ETH',
                to_asset: 'USD',
                price: '2000',
              },
            ],
            message: '',
          });
        }),
      );

      const { fetchLatestPrices } = useAssetPricesApi();
      const result = await fetchLatestPrices();

      expect(capturedBody).toBeNull();
      expect(result).toHaveLength(1);
      expect(result[0].fromAsset).toBe('ETH');
    });

    it('should send POST request with snake_case payload', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest/all`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: [],
            message: '',
          });
        }),
      );

      const { fetchLatestPrices } = useAssetPricesApi();
      const payload: Partial<ManualPricePayload> = {
        fromAsset: 'BTC',
      };
      await fetchLatestPrices(payload);

      expect(capturedBody).toEqual({
        from_asset: 'BTC',
      });
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/prices/latest/all`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch latest prices',
          })),
      );

      const { fetchLatestPrices } = useAssetPricesApi();

      await expect(fetchLatestPrices())
        .rejects
        .toThrow('Failed to fetch latest prices');
    });
  });

  describe('addLatestPrice', () => {
    it('should send PUT request with snake_case payload', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/prices/latest`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addLatestPrice } = useAssetPricesApi();
      const payload: ManualPriceFormPayload = {
        fromAsset: 'ETH',
        toAsset: 'USD',
        price: '2500',
      };
      const result = await addLatestPrice(payload);

      expect(capturedBody).toEqual({
        from_asset: 'ETH',
        to_asset: 'USD',
        price: '2500',
      });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/prices/latest`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid price',
          })),
      );

      const { addLatestPrice } = useAssetPricesApi();

      await expect(addLatestPrice({
        fromAsset: 'ETH',
        toAsset: 'USD',
        price: '-1',
      }))
        .rejects
        .toThrow('Invalid price');
    });
  });

  describe('deleteLatestPrice', () => {
    it('should send DELETE request with asset in body', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/prices/latest`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteLatestPrice } = useAssetPricesApi();
      const result = await deleteLatestPrice('ETH');

      expect(capturedBody).toEqual({
        asset: 'ETH',
      });
      expect(result).toBe(true);
    });

    it('should throw error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/prices/latest`, () =>
          HttpResponse.json({
            result: null,
            message: 'Asset price not found',
          })),
      );

      const { deleteLatestPrice } = useAssetPricesApi();

      await expect(deleteLatestPrice('UNKNOWN'))
        .rejects
        .toThrow('Asset price not found');
    });
  });

  describe('fetchNftsPrices', () => {
    it('should send POST request and parses response', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/nfts/prices`, () =>
          HttpResponse.json({
            result: [
              {
                asset: 'nft_123',
                manually_input: false,
                price_asset: 'ETH',
                price_in_asset: '0.5',
                price: '1000',
              },
            ],
            message: '',
          })),
      );

      const { fetchNftsPrices } = useAssetPricesApi();
      const result = await fetchNftsPrices();

      expect(result).toHaveLength(1);
      expect(result[0].asset).toBe('nft_123');
      expect(result[0].manuallyInput).toBe(false);
      expect(result[0].priceAsset).toBe('ETH');
    });

    it('should throw error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/nfts/prices`, () =>
          HttpResponse.json({
            result: null,
            message: 'NFT prices unavailable',
          })),
      );

      const { fetchNftsPrices } = useAssetPricesApi();

      await expect(fetchNftsPrices())
        .rejects
        .toThrow('NFT prices unavailable');
    });
  });
});
