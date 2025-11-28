import type { NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNftBalancesApi } from './nft';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/nft', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchNfBalancesTask', () => {
    it('fetches NFT balances as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/nfts/balances`, ({ request }) => {
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

      const { fetchNfBalancesTask } = useNftBalancesApi();
      const payload: NonFungibleBalancesRequestPayload = {
        limit: 50,
        offset: 0,
      };
      const result = await fetchNfBalancesTask(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('limit')).toBe('50');
      expect(capturedParams!.get('offset')).toBe('0');
      expect(result.taskId).toBe(123);
    });

    it('includes optional filters in snake_case', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/nfts/balances`, ({ request }) => {
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

      const { fetchNfBalancesTask } = useNftBalancesApi();
      const payload: NonFungibleBalancesRequestPayload = {
        limit: 100,
        offset: 10,
        name: 'CryptoPunk',
        collectionName: 'CryptoPunks',
        ignoredAssetsHandling: 'exclude',
      };
      await fetchNfBalancesTask(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('name')).toBe('CryptoPunk');
      expect(capturedParams!.get('collection_name')).toBe('CryptoPunks');
      expect(capturedParams!.get('ignored_assets_handling')).toBe('exclude');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/nfts/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch NFT balances',
          })),
      );

      const { fetchNfBalancesTask } = useNftBalancesApi();

      await expect(fetchNfBalancesTask({ limit: 50, offset: 0 }))
        .rejects
        .toThrow('Failed to fetch NFT balances');
    });
  });

  describe('fetchNfBalances', () => {
    it('fetches NFT balances synchronously and parses response', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/nfts/balances`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              entries: [
                {
                  id: 'nft_1',
                  name: 'Cool NFT',
                  collection_name: 'Cool Collection',
                  image_url: 'https://example.com/nft.png',
                  is_lp: false,
                  manually_input: false,
                  price_asset: 'ETH',
                  price_in_asset: '0.5',
                  usd_price: '1000',
                },
              ],
              entries_found: 1,
              entries_limit: 50,
              entries_total: 1,
              total_usd_value: '1000',
            },
            message: '',
          });
        }),
      );

      const { fetchNfBalances } = useNftBalancesApi();
      const result = await fetchNfBalances({ limit: 50, offset: 0 });

      expect(capturedParams!.get('async_query')).toBe('false');
      expect(result.entries).toHaveLength(1);
      expect(result.entries[0].id).toBe('nft_1');
      expect(result.entries[0].name).toBe('Cool NFT');
      expect(result.entries[0].collectionName).toBe('Cool Collection');
      expect(result.entriesFound).toBe(1);
    });

    it('handles nullable fields', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/nfts/balances`, () =>
          HttpResponse.json({
            result: {
              entries: [
                {
                  id: 'nft_2',
                  name: null,
                  collection_name: null,
                  image_url: null,
                  is_lp: null,
                  manually_input: false,
                  price_asset: 'ETH',
                  price_in_asset: '0',
                  usd_price: '0',
                },
              ],
              entries_found: 1,
              entries_limit: 50,
              entries_total: 1,
            },
            message: '',
          })),
      );

      const { fetchNfBalances } = useNftBalancesApi();
      const result = await fetchNfBalances({ limit: 50, offset: 0 });

      expect(result.entries[0].name).toBeNull();
      expect(result.entries[0].collectionName).toBeNull();
      expect(result.entries[0].imageUrl).toBeNull();
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/nfts/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'NFT service unavailable',
          })),
      );

      const { fetchNfBalances } = useNftBalancesApi();

      await expect(fetchNfBalances({ limit: 50, offset: 0 }))
        .rejects
        .toThrow('NFT service unavailable');
    });
  });
});
