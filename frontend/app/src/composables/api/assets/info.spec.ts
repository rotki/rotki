import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const backendUrl = process.env.VITE_BACKEND_URL;
const colibriUrl = process.env.VITE_COLIBRI_URL;

vi.unmock('@/composables/api/assets/info');

describe('composables/api/assets/info', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function getApi(): Promise<ReturnType<typeof import('./info').useAssetInfoApi>> {
    const { useAssetInfoApi } = await import('./info');
    return useAssetInfoApi();
  }

  describe('assetMapping', () => {
    it('fetches asset mapping for identifiers', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${colibriUrl}/assets/mappings`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              assets: {
                ETH: {
                  name: 'Ethereum',
                  symbol: 'ETH',
                  asset_type: 'own chain',
                  is_custom_asset: false,
                  collection_id: null,
                },
                BTC: {
                  name: 'Bitcoin',
                  symbol: 'BTC',
                  asset_type: 'own chain',
                  is_custom_asset: false,
                  collection_id: null,
                },
              },
              asset_collections: {},
            },
            message: '',
          });
        }),
      );

      const { assetMapping } = await getApi();
      const result = await assetMapping(['ETH', 'BTC']);

      expect(capturedBody).toEqual({ identifiers: ['ETH', 'BTC'] });
      expect(result.assets.ETH).toBeDefined();
      expect(result.assets.ETH.name).toBe('Ethereum');
      expect(result.assets.BTC.symbol).toBe('BTC');
    });

    it('handles empty identifiers', async () => {
      server.use(
        http.post(`${colibriUrl}/assets/mappings`, () =>
          HttpResponse.json({
            result: {
              assets: {},
              asset_collections: {},
            },
            message: '',
          })),
      );

      const { assetMapping } = await getApi();
      const result = await assetMapping([]);

      expect(result.assets).toEqual({});
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${colibriUrl}/assets/mappings`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch mappings',
          })),
      );

      const { assetMapping } = await getApi();

      await expect(assetMapping(['ETH']))
        .rejects
        .toThrow('Failed to fetch mappings');
    });
  });

  describe('assetSearch', () => {
    it('searches assets with basic query', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/search/levenshtein`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: [
              {
                identifier: 'ETH',
                name: 'Ethereum',
                symbol: 'ETH',
                asset_type: 'own chain',
              },
              {
                identifier: 'eip155:1/erc20:0x1234',
                name: 'Ethereum Token',
                symbol: 'ETHTK',
                asset_type: 'evm token',
              },
            ],
            message: '',
          });
        }),
      );

      const { assetSearch } = await getApi();
      const result = await assetSearch({ value: 'eth' });

      expect(capturedBody).toEqual({
        value: 'eth',
        limit: 25,
      });
      expect(result).toHaveLength(2);
      expect(result[0].identifier).toBe('ETH');
    });

    it('searches with all parameters', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/assets/search/levenshtein`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: [
              {
                identifier: 'eip155:1/erc20:0x1234',
                name: 'Test Token',
                symbol: 'TEST',
                asset_type: 'evm token',
              },
            ],
            message: '',
          });
        }),
      );

      const { assetSearch } = await getApi();
      await assetSearch({
        value: 'test',
        evmChain: 'ethereum',
        assetType: 'evm token',
        address: '0x1234',
        limit: 10,
        searchNfts: true,
      });

      expect(capturedBody).toEqual({
        value: 'test',
        evm_chain: 'ethereum',
        asset_type: 'evm token',
        address: '0x1234',
        limit: 10,
        search_nfts: true,
      });
    });

    it('handles empty search results', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/search/levenshtein`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { assetSearch } = await getApi();
      const result = await assetSearch({ value: 'nonexistent' });

      expect(result).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/assets/search/levenshtein`, () =>
          HttpResponse.json({
            result: null,
            message: 'Search failed',
          })),
      );

      const { assetSearch } = await getApi();

      await expect(assetSearch({ value: 'eth' }))
        .rejects
        .toThrow('Search failed');
    });
  });

  describe('erc20details', () => {
    it('fetches ERC20 details as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/evm/erc20details`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { erc20details } = await getApi();
      const result = await erc20details({
        address: '0x1234567890abcdef1234567890abcdef12345678',
        evmChain: 'ethereum',
      });

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('address')).toBe('0x1234567890abcdef1234567890abcdef12345678');
      expect(capturedParams!.get('evm_chain')).toBe('ethereum');
      expect(result.taskId).toBe(123);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/evm/erc20details`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch ERC20 details',
          })),
      );

      const { erc20details } = await getApi();

      await expect(erc20details({
        address: '0x1234',
        evmChain: 'ethereum',
      }))
        .rejects
        .toThrow('Failed to fetch ERC20 details');
    });
  });
});
