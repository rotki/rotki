import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDefiApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/defi/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchAirdrops', () => {
    it('fetches airdrops as async task', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/airdrops`, ({ request }) => {
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

      const { fetchAirdrops } = useDefiApi();
      const result = await fetchAirdrops();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/airdrops`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch airdrops',
          })),
      );

      const { fetchAirdrops } = useDefiApi();

      await expect(fetchAirdrops())
        .rejects
        .toThrow('Failed to fetch airdrops');
    });
  });

  describe('fetchAirdropsMetadata', () => {
    it('fetches airdrops metadata', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/airdrops/metadata`, () =>
          HttpResponse.json({
            result: [
              {
                identifier: 'uniswap',
                name: 'Uniswap',
                icon: 'uniswap.svg',
                iconUrl: 'https://example.com/uniswap.svg',
              },
              {
                identifier: 'aave',
                name: 'Aave',
                icon: 'aave.svg',
              },
            ],
            message: '',
          })),
      );

      const { fetchAirdropsMetadata } = useDefiApi();
      const result = await fetchAirdropsMetadata();

      expect(result).toHaveLength(2);
      expect(result[0].identifier).toBe('uniswap');
      expect(result[0].name).toBe('Uniswap');
      expect(result[0].iconUrl).toBe('https://example.com/uniswap.svg');
      expect(result[1].identifier).toBe('aave');
      expect(result[1].iconUrl).toBeUndefined();
    });

    it('handles empty metadata', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/airdrops/metadata`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { fetchAirdropsMetadata } = useDefiApi();
      const result = await fetchAirdropsMetadata();

      expect(result).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/airdrops/metadata`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch airdrops metadata',
          })),
      );

      const { fetchAirdropsMetadata } = useDefiApi();

      await expect(fetchAirdropsMetadata())
        .rejects
        .toThrow('Failed to fetch airdrops metadata');
    });
  });

  describe('fetchDefiMetadata', () => {
    it('fetches defi metadata', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/defi/metadata`, () =>
          HttpResponse.json({
            result: [
              {
                identifier: 'compound',
                name: 'Compound',
                icon: 'compound.svg',
                iconUrl: 'https://example.com/compound.svg',
              },
              {
                identifier: 'makerdao',
                name: 'MakerDAO',
                icon: 'makerdao.svg',
              },
              {
                identifier: 'yearn',
                name: 'Yearn Finance',
                icon: 'yearn.svg',
                iconUrl: 'https://example.com/yearn.svg',
              },
            ],
            message: '',
          })),
      );

      const { fetchDefiMetadata } = useDefiApi();
      const result = await fetchDefiMetadata();

      expect(result).toHaveLength(3);
      expect(result[0].identifier).toBe('compound');
      expect(result[0].name).toBe('Compound');
      expect(result[1].identifier).toBe('makerdao');
      expect(result[2].identifier).toBe('yearn');
    });

    it('handles empty metadata', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/defi/metadata`, () =>
          HttpResponse.json({
            result: [],
            message: '',
          })),
      );

      const { fetchDefiMetadata } = useDefiApi();
      const result = await fetchDefiMetadata();

      expect(result).toEqual([]);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/defi/metadata`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch defi metadata',
          })),
      );

      const { fetchDefiMetadata } = useDefiApi();

      await expect(fetchDefiMetadata())
        .rejects
        .toThrow('Failed to fetch defi metadata');
    });
  });
});
