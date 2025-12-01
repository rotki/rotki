import type { FetchBlockchainBalancePayload } from '@/types/blockchain/balances';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/types/modules';
import { useBlockchainBalancesApi } from './blockchain';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/balances/blockchain', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('queryLoopringBalances', () => {
    it('fetches loopring balances with async_query param', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/loopring/balances`, ({ request }) => {
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

      const { queryLoopringBalances } = useBlockchainBalancesApi();
      const result = await queryLoopringBalances();

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth/modules/loopring/balances`, () =>
          HttpResponse.json({
            result: null,
            message: 'Loopring query failed',
          })),
      );

      const { queryLoopringBalances } = useBlockchainBalancesApi();

      await expect(queryLoopringBalances())
        .rejects
        .toThrow('Loopring query failed');
    });
  });

  describe('queryBlockchainBalances', () => {
    it('fetches all blockchain balances without specific blockchain', async () => {
      let capturedUrl = '';
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains/:blockchain`, ({ request }) => {
          capturedUrl = request.url;
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

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = { blockchain: 'btc', ignoreCache: false };
      const result = await queryBlockchainBalances(payload);

      expect(capturedUrl).toContain('/balances/blockchains/btc');
      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(456);
    });

    it('fetches specific blockchain balances', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains/eth`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 789,
            },
            message: '',
          });
        }),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: 'eth',
        ignoreCache: false,
      };
      const result = await queryBlockchainBalances(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(result.taskId).toBe(789);
    });

    it('includes addresses and ignore_cache params', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains/eth`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 100,
            },
            message: '',
          });
        }),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: 'eth',
        addresses: ['0x1234', '0x5678'],
        ignoreCache: true,
      };
      await queryBlockchainBalances(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('addresses')).toBe('0x1234,0x5678');
      expect(capturedParams!.get('ignore_cache')).toBe('true');
    });

    it('includes usd_value_threshold when provided', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 200,
            },
            message: '',
          });
        }),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = { blockchain: '', ignoreCache: false };
      await queryBlockchainBalances(payload, '1000');

      expect(capturedParams!.get('usd_value_threshold')).toBe('1000');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/balances/blockchains`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to fetch balances',
          })),
      );

      const { queryBlockchainBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = { blockchain: '', ignoreCache: false };

      await expect(queryBlockchainBalances(payload))
        .rejects
        .toThrow('Failed to fetch balances');
    });
  });

  describe('queryXpubBalances', () => {
    it('fetches xpub balances for specific blockchain', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/btc/xpub`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              task_id: 300,
            },
            message: '',
          });
        }),
      );

      const { queryXpubBalances } = useBlockchainBalancesApi();
      const payload: FetchBlockchainBalancePayload = {
        blockchain: 'btc',
        addresses: ['xpub6ABC123...'],
        ignoreCache: true,
      };
      const result = await queryXpubBalances(payload);

      expect(capturedParams!.get('async_query')).toBe('true');
      expect(capturedParams!.get('xpub')).toBe('xpub6ABC123...');
      expect(capturedParams!.get('ignore_cache')).toBe('true');
      expect(result.taskId).toBe(300);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/btc/xpub`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid xpub',
          })),
      );

      const { queryXpubBalances } = useBlockchainBalancesApi();

      await expect(queryXpubBalances({ blockchain: 'btc', ignoreCache: false }))
        .rejects
        .toThrow('Invalid xpub');
    });
  });

  describe('fetchDetectedTokens', () => {
    it('fetches detected tokens with only_cache param', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              '0x1234': {
                last_update_timestamp: 1700000000,
                tokens: ['0xtoken1', '0xtoken2'],
              },
            },
            message: '',
          });
        }),
      );

      const { fetchDetectedTokens } = useBlockchainBalancesApi();
      const result = await fetchDetectedTokens('eth', ['0x1234']);

      expect(capturedBody).toEqual({
        addresses: ['0x1234'],
        only_cache: true,
      });
      expect(result['0x1234'].tokens).toEqual(['0xtoken1', '0xtoken2']);
    });

    it('handles null addresses', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {},
            message: '',
          });
        }),
      );

      const { fetchDetectedTokens } = useBlockchainBalancesApi();
      await fetchDetectedTokens('eth', null);

      expect(capturedBody).toEqual({
        addresses: null,
        only_cache: true,
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, () =>
          HttpResponse.json({
            result: null,
            message: 'Token detection failed',
          })),
      );

      const { fetchDetectedTokens } = useBlockchainBalancesApi();

      await expect(fetchDetectedTokens('eth', ['0x1234']))
        .rejects
        .toThrow('Token detection failed');
    });
  });

  describe('fetchDetectedTokensTask', () => {
    it('fetches detected tokens as async task', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/eth/tokens/detect`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 400,
            },
            message: '',
          });
        }),
      );

      const { fetchDetectedTokensTask } = useBlockchainBalancesApi();
      const result = await fetchDetectedTokensTask('eth', ['0x1234', '0x5678']);

      expect(capturedBody).toEqual({
        addresses: ['0x1234', '0x5678'],
        async_query: true,
      });
      expect(result.taskId).toBe(400);
    });
  });

  describe('deleteModuleData', () => {
    it('deletes all module data when no module specified', async () => {
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/data`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();
      const result = await deleteModuleData();

      expect(capturedUrl).toContain('/blockchains/eth/modules/data');
      expect(result).toBe(true);
    });

    it('deletes specific module data', async () => {
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/loopring/data`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();
      const result = await deleteModuleData(Module.LOOPRING);

      expect(capturedUrl).toContain('/blockchains/eth/modules/loopring/data');
      expect(result).toBe(true);
    });

    it('handles null module parameter', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/data`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();
      const result = await deleteModuleData(null);

      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth/modules/data`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete module data',
          })),
      );

      const { deleteModuleData } = useBlockchainBalancesApi();

      await expect(deleteModuleData())
        .rejects
        .toThrow('Failed to delete module data');
    });
  });
});
