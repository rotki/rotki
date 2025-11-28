import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetCexMappingApi } from './cex-mapping';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/assets/cex-mapping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchAllCexMapping', () => {
    it('sends POST request with snake_case payload and omits orderByAttributes and ascending', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/locationmappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [
                {
                  location: 'binance',
                  location_symbol: 'BTC',
                  asset: 'BTC',
                },
              ],
              entries_found: 1,
              entries_limit: 10,
              entries_total: 1,
            },
            message: '',
          });
        }),
      );

      const { fetchAllCexMapping } = useAssetCexMappingApi();
      const result = await fetchAllCexMapping({
        limit: 10,
        offset: 0,
        location: 'binance',
        orderByAttributes: ['location'],
        ascending: [true],
      });

      expect(capturedBody).toEqual({
        limit: 10,
        offset: 0,
        location: 'binance',
      });
      expect(capturedBody).not.toHaveProperty('order_by_attributes');
      expect(capturedBody).not.toHaveProperty('ascending');

      expect(result.data).toHaveLength(1);
      expect(result.data[0].location).toBe('binance');
      expect(result.data[0].locationSymbol).toBe('BTC');
      expect(result.data[0].asset).toBe('BTC');
    });

    it('handles ref payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/locationmappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 10,
              entries_total: 0,
            },
            message: '',
          });
        }),
      );

      const { fetchAllCexMapping } = useAssetCexMappingApi();
      const payloadRef = ref({
        limit: 20,
        offset: 10,
      });

      await fetchAllCexMapping(payloadRef);

      expect(capturedBody).toEqual({
        limit: 20,
        offset: 10,
      });
    });

    it('returns collection with pagination info', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/locationmappings`, () =>
          HttpResponse.json({
            result: {
              entries: [
                { location: 'kraken', location_symbol: 'ETH', asset: 'ETH' },
                { location: 'kraken', location_symbol: 'XBT', asset: 'BTC' },
              ],
              entries_found: 2,
              entries_limit: 50,
              entries_total: 100,
            },
            message: '',
          })),
      );

      const { fetchAllCexMapping } = useAssetCexMappingApi();
      const result = await fetchAllCexMapping({ limit: 50, offset: 0 });

      expect(result.data).toHaveLength(2);
      expect(result.found).toBe(2);
      expect(result.limit).toBe(50);
      expect(result.total).toBe(100);
    });
  });

  describe('addCexMapping', () => {
    it('sends PUT request with entries array containing snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/locationmappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addCexMapping } = useAssetCexMappingApi();
      const result = await addCexMapping({
        location: 'coinbase',
        locationSymbol: 'USDT',
        asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
      });

      expect(result).toBe(true);
      expect(capturedBody).toEqual({
        entries: [
          {
            location: 'coinbase',
            location_symbol: 'USDT',
            asset: 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7',
          },
        ],
      });
    });

    it('handles null location', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/assets/locationmappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { addCexMapping } = useAssetCexMappingApi();
      await addCexMapping({
        location: null,
        locationSymbol: 'GLOBAL_SYMBOL',
        asset: 'ETH',
      });

      expect(capturedBody).toEqual({
        entries: [
          {
            location: null,
            location_symbol: 'GLOBAL_SYMBOL',
            asset: 'ETH',
          },
        ],
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/assets/locationmappings`, () =>
          HttpResponse.json({
            result: null,
            message: 'Mapping already exists',
          })),
      );

      const { addCexMapping } = useAssetCexMappingApi();

      await expect(addCexMapping({
        location: 'binance',
        locationSymbol: 'BTC',
        asset: 'BTC',
      }))
        .rejects
        .toThrow('Mapping already exists');
    });
  });

  describe('editCexMapping', () => {
    it('sends PATCH request with entries array containing snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/assets/locationmappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editCexMapping } = useAssetCexMappingApi();
      const result = await editCexMapping({
        location: 'kraken',
        locationSymbol: 'XBT',
        asset: 'BTC',
      });

      expect(result).toBe(true);
      expect(capturedBody).toEqual({
        entries: [
          {
            location: 'kraken',
            location_symbol: 'XBT',
            asset: 'BTC',
          },
        ],
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/assets/locationmappings`, () =>
          HttpResponse.json({
            result: null,
            message: 'Mapping not found',
          })),
      );

      const { editCexMapping } = useAssetCexMappingApi();

      await expect(editCexMapping({
        location: 'unknown',
        locationSymbol: 'XYZ',
        asset: 'ETH',
      }))
        .rejects
        .toThrow('Mapping not found');
    });
  });

  describe('deleteCexMapping', () => {
    it('sends DELETE request with entries array containing snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/locationmappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteCexMapping } = useAssetCexMappingApi();
      const result = await deleteCexMapping({
        location: 'binance',
        locationSymbol: 'ETH',
      });

      expect(result).toBe(true);
      expect(capturedBody).toEqual({
        entries: [
          {
            location: 'binance',
            location_symbol: 'ETH',
          },
        ],
      });
    });

    it('handles null location in delete payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/assets/locationmappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteCexMapping } = useAssetCexMappingApi();
      await deleteCexMapping({
        location: null,
        locationSymbol: 'GLOBAL_SYMBOL',
      });

      expect(capturedBody).toEqual({
        entries: [
          {
            location: null,
            location_symbol: 'GLOBAL_SYMBOL',
          },
        ],
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/assets/locationmappings`, () =>
          HttpResponse.json({
            result: null,
            message: 'Mapping does not exist',
          })),
      );

      const { deleteCexMapping } = useAssetCexMappingApi();

      await expect(deleteCexMapping({
        location: 'coinbase',
        locationSymbol: 'UNKNOWN',
      }))
        .rejects
        .toThrow('Mapping does not exist');
    });
  });
});
